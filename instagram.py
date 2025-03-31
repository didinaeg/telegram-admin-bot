
import re
import logging
import tempfile
from pathlib import Path
import instaloader

logger = logging.getLogger(__name__)

async def download_instagram_post(url: str) -> list[tuple[str, bytes, str]]:
    """Descarga un post de Instagram y devuelve el contenido de los archivos descargados
    
    Returns:
        list[tuple[str, bytes, str]]: Lista de tuplas con (nombre_archivo, contenido_binario, tipo_mime)
    """
    logger.info(f"Descargando post de Instagram: {url}")
    
    # Extraer el código del post de la URL
    match = re.search(r'instagram\.com/(?:p|reels|reel)/([^/]+)', url)
    if not match:
        logger.error(f"No se pudo extraer el código del post de Instagram: {url}")
        return []
    
    shortcode = match.group(1)
    logger.info(f"Código extraído: {shortcode}")
    
    # Configurar instaloader
    L = instaloader.Instaloader(
        download_video_thumbnails=False,
        save_metadata=False,
        download_comments=False,
        download_geotags=False,
        download_pictures=True,
        download_videos=True,
    )
    
    try:
        # Obtener el post
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        media_content = []
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Descargar el post
            success = L.download_post(post, target=temp_path)
            
            if success:
                # Recopilar todos los archivos descargados (imágenes y videos)
                files = list(temp_path.glob('**/*'))
                media_files = [f for f in files if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.mp4']]
                logger.info(f"Archivos descargados: {[str(f) for f in media_files]}")
                
                # Leer el contenido de los archivos dentro del contexto 'with'
                for file_path in media_files:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        
                    # Determinar el tipo MIME basado en la extensión
                    mime_type = ""
                    if file_path.suffix.lower() in ['.jpg', '.jpeg']:
                        mime_type = "image/jpeg"
                    elif file_path.suffix.lower() == '.png':
                        mime_type = "image/png"
                    elif file_path.suffix.lower() == '.mp4':
                        mime_type = "video/mp4"
                        
                    media_content.append((file_path.name, content, mime_type))
                
                return media_content
            else:
                logger.error("Error al descargar el post de Instagram")
                return []
    except Exception as e:
        logger.error(f"Error descargando el post de Instagram: {str(e)}")
        return []
