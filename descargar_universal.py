import os, sys, subprocess
import yt_dlp

BASE_FOLDER_WEB = 'C:/DescargadorUniversal/Descargas'

def actualizar_motor():
    # Actualización silenciosa al arrancar la sesión
    subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], capture_output=True)

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

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
    print("=" * 60)
    print("🌍 DESCARGADOR UNIVERSAL (MODO BUCLE + AUTO-UPDATE)")
    print("=" * 60)
    
    url = input("👉 Pega la URL completa (o escribe 'salir'): ").strip()
    if url.lower() in ['salir', 'exit', 'q']:
        return False

    try:
        print("\n🔍 Identificando origen...")
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'logger': None}) as ydl:
            info_site = ydl.extract_info(url, download=False)
            nombre_sitio = info_site.get('extractor_key', 'Otros').capitalize()

        folder_destino = os.path.join(BASE_FOLDER_WEB, nombre_sitio)
        os.makedirs(folder_destino, exist_ok=True)

        es_youtube = 'Youtube' in nombre_sitio
        formato_final = 'bestvideo+bestaudio/best'

        if es_youtube:
            menu, title = obtener_info_youtube(url)
            if menu:
                print(f"\nCalidades para: {title}")
                lista_ids = []
                for i, (res, datos) in enumerate(menu.items(), 1):
                    print(f"{i}. {res}p -> {datos['peso']}")
                    lista_ids.append(datos['id'])
                print(f"{len(lista_ids) + 1}. Cancelar")
                
                sel = input("\nElije opción: ")
                if sel.isdigit() and 1 <= int(sel) <= len(lista_ids):
                    formato_final = lista_ids[int(sel)-1]
                else: 
                    print("🛑 Cancelado."); time.sleep(1); return True
        else:
            print(f"\n🌍 Web: {nombre_sitio}. Descargando...")

        ydl_opts_dl = {
            'format': formato_final,
            'outtmpl': f"{folder_destino}/%(title)s.%(ext)s",
            'merge_output_format': 'mp4',
            'quiet': True, 'no_warnings': True, 'logger': None, 'noprogress': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
            ydl.download([url])
            
        print(f"\n✅ ¡Listo! Guardado en {nombre_sitio}")

    except Exception:
        print(f"\n❌ Error: El enlace no es válido o el sitio no es compatible.")
    
    input("\nPresiona ENTER para seguir descargando...")
    return True

if __name__ == "__main__":
    import time
    actualizar_motor()
    while True:
        if not ejecutar_descarga():
            break
