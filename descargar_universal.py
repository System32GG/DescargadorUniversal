import os, sys, subprocess, urllib.request, json, time, zipfile

# ── Colores ANSI ──────────────────────────────────────────────
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def p(color, texto):
    """Imprime con color ANSI, con fallback seguro si la consola no lo soporta."""
    try:
        print(f"{color}{texto}{RESET}")
    except:
        print(texto)

# ─────────────────────────────────────────────────────────────

def descargar_con_progreso(url, path, descripcion):
    """Descarga un archivo mostrando una barra de progreso en consola."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = 1024 * 8
            downloaded = 0
            with open(path, 'wb') as f:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    f.write(buffer)
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        bar = ('#' * (percent // 2)).ljust(50)
                        try:
                            print(f"\r{CYAN}{descripcion}{RESET}: [{GREEN}{bar}{RESET}] {percent}% ({downloaded//1024} KB)", end='', flush=True)
                        except:
                            print(f"\r{descripcion}: [{bar}] {percent}% ({downloaded//1024} KB)", end='', flush=True)
            print("\n")
        return True
    except Exception as e:
        p(RED, f"\n[ERROR] Durante la descarga: {e}")
        return False

def buscar_ffmpeg_universal():
    """Busca FFmpeg en todas las unidades del sistema con profundidad limitada."""
    import string
    p(CYAN, "[INFO] Buscando FFmpeg en el sistema (esto puede tardar unos segundos)...")
    drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    for drive in drives:
        try:
            if os.path.exists(os.path.join(drive, 'ffmpeg.exe')):
                return os.path.join(drive, 'ffmpeg.exe')
            with os.scandir(drive) as it:
                for entry in it:
                    if entry.is_dir() and 'ffmpeg' in entry.name.lower():
                        p_root = os.path.join(entry.path, 'ffmpeg.exe')
                        p_bin  = os.path.join(entry.path, 'bin', 'ffmpeg.exe')
                        if os.path.exists(p_root): return p_root
                        if os.path.exists(p_bin):  return p_bin
        except:
            continue
    return None

def obtener_internal_dir():
    """Obtiene la ruta en AppData/Local para guardar binarios y config de forma discreta."""
    path = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'Universal_Downloader_Pro_Data')
    os.makedirs(path, exist_ok=True)
    return path

def cargar_config():
    config_path = os.path.join(obtener_internal_dir(), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except: pass
    return {}

def guardar_config(data):
    internal_dir = obtener_internal_dir()
    config_path = os.path.join(internal_dir, 'config.json')
    try:
        with open(config_path, 'w') as f:
            json.dump(data, f)
    except: pass

def asegurar_ffmpeg():
    """Verifica si FFmpeg existe; busca universalmente antes de descargar."""
    internal_dir = obtener_internal_dir()

    config = cargar_config()
    ffmpeg_path = config.get('ffmpeg_path')

    if ffmpeg_path and os.path.exists(ffmpeg_path):
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        if ffmpeg_dir not in os.environ['PATH']:
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
        return True

    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except: pass

    local_ffmpeg = os.path.join(internal_dir, 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg):
        os.environ['PATH'] = internal_dir + os.pathsep + os.environ['PATH']
        return True

    path_encontrado = buscar_ffmpeg_universal()
    if path_encontrado:
        p(GREEN, f"[OK] FFmpeg encontrado en: {path_encontrado}")
        config['ffmpeg_path'] = path_encontrado
        guardar_config(config)
        ffmpeg_dir = os.path.dirname(path_encontrado)
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ['PATH']
        return True

    p(YELLOW, "[INFO] No se encontro FFmpeg en ningun lado. Iniciando descarga...")
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = os.path.join(internal_dir, 'ffmpeg.zip')

    if descargar_con_progreso(url, zip_path, "Descargando FFmpeg"):
        try:
            p(CYAN, "[INFO] Extrayendo...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith('ffmpeg.exe') or file.endswith('ffprobe.exe'):
                        filename = os.path.basename(file)
                        with zip_ref.open(file) as source, open(os.path.join(internal_dir, filename), 'wb') as target:
                            target.write(source.read())
            os.remove(zip_path)
            config['ffmpeg_path'] = os.path.join(internal_dir, 'ffmpeg.exe')
            guardar_config(config)
            os.environ['PATH'] = internal_dir + os.pathsep + os.environ['PATH']
            p(GREEN, "[OK] FFmpeg configurado correctamente.")
            return True
        except Exception as e:
            p(RED, f"[ERROR] No se pudo extraer FFmpeg: {e}")
    return False

def actualizar_ytdlp_portable():
    """Descarga la ultima version de yt-dlp desde GitHub si es necesario."""
    try:
        internal_dir = obtener_internal_dir()
        update_file = os.path.join(internal_dir, 'yt-dlp.zip')

        p(CYAN, "[INFO] Comprobando actualizaciones de motor...")

        api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(api_url, headers=headers)

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            latest_version = data['tag_name']

            config = cargar_config()
            current_version = config.get('ytdlp_version', '')

            if current_version == latest_version and os.path.exists(update_file):
                p(GREEN, f"[OK] Motor al dia (version {latest_version}).")
                sys.path.insert(0, update_file)
                return

            download_url = next((a['browser_download_url'] for a in data['assets'] if a['name'] == 'yt-dlp'), None)

            if download_url:
                if descargar_con_progreso(download_url, update_file, f"Actualizando motor a {latest_version}"):
                    config['ytdlp_version'] = latest_version
                    guardar_config(config)

        if os.path.exists(update_file):
            sys.path.insert(0, update_file)

    except Exception as e:
        p(YELLOW, f"[WARN] No se pudo comprobar actualizaciones: {e}")
        update_file = os.path.join(obtener_internal_dir(), 'yt-dlp.zip')
        if os.path.exists(update_file):
            sys.path.insert(0, update_file)

import yt_dlp

DEFAULT_FOLDER_WEB = 'C:/DescargadorUniversal/Descargas'

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def obtener_ruta_sistema(nombre):
    """Obtiene la ruta real de carpetas de sistema, considerando OneDrive."""
    home = os.path.expanduser("~")
    standard = os.path.join(home, nombre)
    onedrive = os.path.join(home, "OneDrive", nombre)
    
    if os.path.exists(onedrive):
        return onedrive
    return standard

def elegir_carpeta():
    """Muestra carpetas recomendadas y permite elegir o escribir una ruta."""
    config = cargar_config()
    ultima = config.get('ultima_carpeta_universal', DEFAULT_FOLDER_WEB)

    recomendaciones = [
        ("Escritorio",    obtener_ruta_sistema("Desktop")),
        ("Descargas",     obtener_ruta_sistema("Downloads")),
        ("Documentos",    obtener_ruta_sistema("Documents")),
        ("Videos",        obtener_ruta_sistema("Videos")),
        ("Ultima usada",  ultima),
    ]

    print("")
    p(CYAN,   "=" * 60)
    p(BOLD,   "   CARPETA DE DESTINO")
    p(CYAN,   "=" * 60)
    for i, (nombre, ruta) in enumerate(recomendaciones, 1):
        print(f"  {BOLD}{i}.{RESET} {nombre:<14} {YELLOW}{ruta}{RESET}")
    print(f"  {BOLD}{len(recomendaciones)+1}.{RESET} Escribir ruta personalizada")
    print("")

    try:
        sel = input("  >> Opcion (ENTER = ultima usada): ").strip()
    except:
        sel = ""

    if sel.isdigit():
        idx = int(sel) - 1
        if 0 <= idx < len(recomendaciones):
            carpeta = recomendaciones[idx][1]
        else:
            try:
                carpeta = input("  >> Ruta: ").strip() or ultima
            except:
                carpeta = ultima
    elif sel == "":
        carpeta = ultima
    else:
        carpeta = sel

    config['ultima_carpeta_universal'] = carpeta
    guardar_config(config)
    os.makedirs(carpeta, exist_ok=True)
    p(GREEN, f"  [OK] Guardando en: {carpeta}")
    print("")
    return carpeta

def obtener_info_youtube(url):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'format_sort': ['res', 'ext:mp4:m4a'], 'logger': None}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            best_audio = next((f for f in formats[::-1] if f.get('vcodec') == 'none' and 'm3u8' not in (f.get('url') or '')), None)
            audio_size = best_audio.get('filesize') or best_audio.get('filesize_approx') or 0
            opciones = {}
            for f in formats:
                h = f.get('height')
                if h and f.get('vcodec') != 'none' and 'm3u8' not in (f.get('url') or ''):
                    if h not in opciones:
                        f_size = f.get('filesize') or f.get('filesize_approx')
                        peso = f"~{( (f_size + audio_size) / (1024*1024) ):.1f} MB" if f_size else "Peso N/D"
                        opciones[h] = {'peso': peso, 'id': f"{f['format_id']}+{best_audio['format_id']}" if best_audio else f['format_id']}
            return dict(sorted(opciones.items(), reverse=True)), info.get('title', 'Video')
        except: return None, None

def ejecutar_descarga():
    limpiar_pantalla()
    p(CYAN, "=" * 60)
    p(BOLD, "   DESCARGADOR UNIVERSAL")
    p(CYAN, "=" * 60)

    # Elegir carpeta ANTES de pedir la URL
    folder_base = elegir_carpeta()

    url = input(">> Pega la URL completa (o escribe 'salir'): ").strip()
    if url.lower() in ['salir', 'exit', 'q']:
        return False

    try:
        p(CYAN, "\n[INFO] Identificando origen...")
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'logger': None}) as ydl:
            info_site = ydl.extract_info(url, download=False)
            nombre_sitio = info_site.get('extractor_key', 'Otros').capitalize()

        folder_destino = os.path.join(folder_base, nombre_sitio)
        os.makedirs(folder_destino, exist_ok=True)

        es_youtube = 'Youtube' in nombre_sitio
        formato_final = 'bestvideo+bestaudio/best'

        if es_youtube:
            menu, title = obtener_info_youtube(url)
            if menu:
                p(CYAN, f"\nCalidades para: {title}")
                lista_ids = []
                for i, (res, datos) in enumerate(menu.items(), 1):
                    print(f"  {BOLD}{i}.{RESET} {res}p  ->  {datos['peso']}")
                    lista_ids.append(datos['id'])
                print(f"  {BOLD}{len(lista_ids) + 1}.{RESET} Cancelar")

                sel = input("\n>> Elije opcion: ")
                if sel.isdigit() and 1 <= int(sel) <= len(lista_ids):
                    formato_final = lista_ids[int(sel)-1]
                else:
                    p(YELLOW, "Cancelado."); time.sleep(1); return True
        else:
            p(CYAN, f"\nSitio: {nombre_sitio}. Descargando en maxima calidad...")

        ydl_opts_dl = {
            'format': formato_final,
            'outtmpl': f"{folder_destino}/%(title)s.%(ext)s",
            'merge_output_format': 'mp4',
            'quiet': True, 'no_warnings': True, 'logger': None, 'noprogress': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
            ydl.download([url])

        p(GREEN, f"\n[OK] Listo! Guardado en: {folder_destino}")

    except Exception:
        p(RED, "\n[ERROR] El enlace no es valido o el sitio no es compatible.")

    input("\nPresiona ENTER para seguir descargando...")
    return True

if __name__ == "__main__":
    try:
        asegurar_ffmpeg()
        actualizar_ytdlp_portable()

        while True:
            if not ejecutar_descarga():
                break
    except Exception as e:
        import traceback
        p(RED, "\n" + "="*60)
        p(RED, "   CRITICAL ERROR / ERROR CRÍTICO")
        p(RED, "="*60)
        p(YELLOW, f"Detalles: {e}")
        print("\nTraza del error:")
        print(traceback.format_exc())
        p(RED, "="*60)
        input("\nPresiona ENTER para cerrar...")
