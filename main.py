import threading
from typing import Optional
import instaloader
import tempfile
from pathlib import Path
import re
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
    ChatMemberUpdated,
    Update,
    Message,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    PicklePersistence,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackContext,
    ChatMemberHandler,
    filters,
)

from urllib.parse import urlparse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from conversations.video_download import (
    download_no,
    download_start,
    download_yes,
    stop_callback,
)
from estados import DOWNLOAD_CHOOSING, DOWNLOADING
from messages import RULES_MESSAGE, MENSAJES_INTERVALOS
from utils import extract_status_change, restricted

import logging
import os
from dotenv import load_dotenv
import random

load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

class CustomHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Hello, world!")

    def log_message(self, format: str, *args: Optional[str]) -> None:
        return  # Disable logging for HTTP requests

class MyServer(threading.Thread):
    def run(self):
        logger.info("Iniciando servidor HTTP en el puerto 8080")
        self.server = ThreadingHTTPServer(('', 8080), CustomHTTPRequestHandler)
        self.server.serve_forever()
    def stop(self):
        self.server.shutdown()


# Función para manejar el comando /start
async def start_handler(update: Update, context: CallbackContext) -> None:
    user = update.effective_user

    if user is None or update.message is None:
        return

    logger.info(f"El usuario {user.first_name} ha iniciado una conversación.")
    message = (
        f"Hola, [{user.first_name}](tg://user?id={user.id}) soy Manolito,\n"
        "estoy aquí para ayudarte con la gestión de tu bar\n"
        "\¿qué necitas\?"  # type: ignore
    )
    await update.message.reply_text(message, parse_mode="MarkdownV2")


async def greet_new_member(update: Update, context: CallbackContext) -> None:
    if (
        update.chat_member is None
        or update.chat_member.new_chat_member is None
        or update.effective_chat is None
    ):
        return

    result = extract_status_change(update.chat_member)
    if result is None:
        logger.info("No se detectó un cambio en el estado del miembro.")
        return

    was_member, is_member = result
    cause_name = update.chat_member.from_user.mention_markdown_v2()
    member_name = update.chat_member.new_chat_member.user.name
    member_name_mention = update.chat_member.new_chat_member.user.mention_markdown_v2()
    member_id = update.chat_member.new_chat_member.user.id
    logger.info(
        f"El estado del miembro {member_name} (id: {member_id}) ha cambiado de {was_member} a {is_member}. Causado por {cause_name}."
    )
    # Saludar si el usuario pasó de no ser miembro a ser miembro
    if not was_member and is_member:
        logger.info(f"Saludando a {member_name} por unirse al grupo.")
        message = (
            f"¡Bienvenido al Bar de Manolo {member_name_mention}\!\n"  # type: ignore
            "Para poder ser aceptado en el grupo envía lo siguiente:\n"
            "\- Dirección\n"  # type: ignore
            "\- Objetos de valor y dónde los guarda\n"  # type: ignore
            "\- Tipo sanguíneo\n"  # type: ignore
            "No nos hacemos responsables de daños o perjuicios hacia su propiedad privada \(por favor consulta las /rules\)"  # type: ignore
        )
        await update.effective_chat.send_message(
            message,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    elif was_member and not is_member:
        logger.warning(f"Despidiendo a {member_name} por salir del grupo.")


async def rules_handler(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return
    await update.message.reply_text(RULES_MESSAGE, parse_mode=ParseMode.MARKDOWN_V2)


async def all_messages_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return
    
    print(f"El usuario {user.first_name} (id: {user.id}) ha enviado un mensaje.")
    message = update.message.text
    
    if message is None:
        return

    # Comprobar si el mensaje contiene un enlace.
    try:
        url = urlparse(message)
        url_link = url.geturl()
        # Check if the url a youtube link
        youtube_domains = ["www.youtube.com", "youtube.com", "youtu.be"]
        if url.hostname in youtube_domains:
            logger.info(
                f"El usuario {user.first_name} ha enviado un enlace de YouTube."
            )
            buttons = [
                [
                    InlineKeyboardButton(
                        text="Iniciar descarga",
                        callback_data=f"start_download:{url_link}",
                    )
                ],
            ]
            keyboard = InlineKeyboardMarkup(buttons)

            await update.message.reply_text(
                f"Haz clic en el botón para iniciar el proceso de descarga para:\n{url_link}",
                reply_markup=keyboard,
            )

        instagram_domains = ["www.instagram.com", "instagram.com"]
        if url.hostname in instagram_domains:
            logger.info(
                f"El usuario {user.first_name} ha enviado un enlace de Instagram."
            )
            await update.message.reply_text(
                "Descargando contenido de Instagram, por favor espera..."
            )
            
            # Descargar el post de Instagram
            media_contents = await download_instagram_post(url_link)
            
            if media_contents:
                # Enviar cada archivo como respuesta al mensaje original
                for filename, content, mime_type in media_contents:
                    from io import BytesIO
                    file_obj = BytesIO(content)
                    file_obj.name = filename
                    
                    if mime_type.startswith('image/'):
                        await update.message.reply_photo(
                            photo=file_obj,
                            caption=f"Contenido descargado de Instagram"
                        )
                    elif mime_type.startswith('video/'):
                        await update.message.reply_video(
                            video=file_obj,
                            caption=f"Contenido descargado de Instagram"
                        )
                        
                await update.message.reply_text("¡Descarga de Instagram completada!")
            else:
                await update.message.reply_text(
                    "Lo siento, no pude descargar el contenido de Instagram."
                )

        tiktok_domains = ["www.tiktok.com", "tiktok.com"]
        if url.hostname in tiktok_domains:
            logger.info(f"El usuario {user.first_name} ha enviado un enlace de TikTok.")
            await update.message.reply_text(
                "No se pueden enviar enlaces de TikTok en este grupo."
            )
    except:
        pass


async def callback_auto_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje automático usando el chat_id almacenado en job.data"""
    if context.job is None or context.job.chat_id is None:
        return
    chat_id = context.job.chat_id  # En v20+ se usa job.data en lugar de context
    # Enviar mensaje aleatorio de la lista MENSAJES_INTERVALOS
    mensaje = random.choice(MENSAJES_INTERVALOS).replace(".", "\.").replace("-", "\-").replace("(", "\(").replace(")", "\)").replace("_", "\_").replace("[", "\[").replace("]", "\]").replace("!", "\!")  # type: ignore
    await context.bot.send_message(chat_id=chat_id, text=MENSAJES_INTERVALOS[0])

@restricted
async def start_auto_messaging(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Inicia el envío de mensajes automáticos"""
    logger.info("Iniciando mensajes automáticos")
    if update.effective_chat is None or update.effective_message is None or context.job_queue is None:
        return
    chat_id = update.effective_message.chat.id
    intervalo = 60 * 60 * 13
    # check if the user is an admin
    context.job_queue.run_repeating(
        callback_auto_message, intervalo, chat_id=chat_id, name=str(chat_id)
    )
    logger.info(f"Job creado para enviar mensajes automáticos a {chat_id}")
    # Alternativas comentadas:
    # context.job_queue.run_once(callback_auto_message, 3600, data=chat_id)
    # context.job_queue.run_daily(callback_auto_message, time=datetime.time(hour=9, minute=22), days=(0, 1, 2, 3, 4, 5, 6), data=chat_id)

    await update.effective_message.reply_text("¡Mensajes automáticos iniciados!")


async def stop_notify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detiene el envío de mensajes automáticos"""
    if update.effective_chat is None or update.message is None:
        return

    chat_id = update.effective_chat.id
    if context.job_queue is None:
        return
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if jobs:
        for job in jobs:
            job.schedule_removal()
        await update.message.reply_text("¡Mensajes automáticos detenidos!")
    else:
        await update.message.reply_text("No hay mensajes automáticos activos.")


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


def main() -> None:
    # run_parallel_http_server()
    s = MyServer()
    s.start()

    # Reemplaza 'YOUR_TOKEN' con el token de tu bot
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if TELEGRAM_BOT_TOKEN is None:
        logger.error(
            "No se encontró el token del bot en la variable de entorno TELEGRAM_BOT_TOKEN"
        )
        return

    persistence_helper = PicklePersistence(filepath="persistence.pkl")

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .persistence(persistence=persistence_helper)
        .build()
    )

    # Añadir manejador para el comando /start
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("rules", rules_handler))
    application.add_handler(
        ChatMemberHandler(greet_new_member, ChatMemberHandler.CHAT_MEMBER)
    )  # Se completa el ChatMemberHandler para saludar a nuevos usuarios

    # Run the bot until the user presses Ctrl-C
    application.add_handler(CommandHandler("auto", start_auto_messaging))
    application.add_handler(CommandHandler("stop", stop_notify))
    # Conversación para descarga de videos (ahora todos son CallbackQueryHandler)
    application.add_handler(MessageHandler(filters.ALL, all_messages_handler))
    download_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(download_start, pattern="^start_download:")],
        states={
            DOWNLOAD_CHOOSING: [
                CallbackQueryHandler(download_yes, pattern="^download_yes$"),
                CallbackQueryHandler(download_no, pattern="^download_no$"),
            ],
            DOWNLOADING: [],  # Este estado sólo espera que termine la descarga
        },
        fallbacks=[CallbackQueryHandler(stop_callback, pattern="^download_cancel$")],
        conversation_timeout=60 * 10,
        block=False,
        per_message=True,
        per_user=False,
        per_chat=True,
    )

    application.add_handler(download_conv)
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Deteniendo el bot...")
    finally:
        logger.info("Servidor HTTP cerrado.")
        s.stop()
        s.join()
if __name__ == "__main__":
    main()
