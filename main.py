import datetime
import threading
from typing import Optional
import instaloader
import tempfile
from pathlib import Path
import re
import base64
from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
    ChatMemberUpdated,
    Update,
    Message,
    InlineQueryResultArticle,
    InputTextMessageContent,
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
    InlineQueryHandler,
    filters,
)
from io import BytesIO
from uuid import uuid4

from urllib.parse import urlparse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from admin import ban_handler, unban_handler, unrestrict_handler
# Importar módulos personalizados
from estados import DOWNLOAD_CHOOSING, DOWNLOADING
from instagram import download_instagram_post
from messages import RULES_MESSAGE, MENSAJES_INTERVALOS
from utils import ADMIN_CHAT_ID, extract_status_change, isAdmin, restricted

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
        self.server = ThreadingHTTPServer(("", 8080), CustomHTTPRequestHandler)
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
        f"Hola, [{user.first_name}](tg://user?id={user.id}) soy Adolf,\n"
        "estoy aquí para ayudarte\n"
        "¿qué necitas\?\n" # type: ignore
        "manda fotopies"  
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
        b_message = await update.effective_chat.send_message(
            message,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        # Programar la eliminación del mensaje después de 10 minutos
        if context.job_queue:
            delete_time = 10 * 60  # 10 minutos en segundos
            if update.effective_chat is None:
                return
            context.job_queue.run_once(
                delete_message_callback,
                delete_time,
                data={
                    "chat_id": update.effective_chat.id,
                    "message_id": b_message.message_id,
                },
            )
            logger.info(
                f"Programada eliminación automática del mensaje de reglas en {delete_time} segundos"
            )
    elif was_member and not is_member:
        logger.warning(f"Despidiendo a {member_name} por salir del grupo.")


async def delete_message_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback para eliminar un mensaje específico"""
    if context.job is None or context.job.data is None:
        return
    job_data = context.job.data
    if not isinstance(job_data, dict):
        return
    chat_id = job_data.get("chat_id")
    message_id = job_data.get("message_id")

    try:
        if chat_id is None or message_id is None:
            return
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(
            f"Mensaje {message_id} eliminado automáticamente del chat {chat_id}"
        )
    except Exception as e:
        logger.error(f"No se pudo eliminar el mensaje: {e}")


async def rules_handler(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return
    rules_message = await update.message.reply_text(
        RULES_MESSAGE, parse_mode=ParseMode.MARKDOWN_V2
    )

    # Programar la eliminación del mensaje después de 10 minutos
    if context.job_queue:
        delete_time = 10 * 60  # 10 minutos en segundos
        if update.effective_chat is None:
            return
        context.job_queue.run_once(
            delete_message_callback,
            delete_time,
            data={
                "chat_id": update.effective_chat.id,
                "message_id": rules_message.message_id,
            },
        )
        logger.info(
            f"Programada eliminación automática del mensaje de reglas en {delete_time} segundos"
        )



async def all_messages_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:

    if update.effective_message is None:
        return

    if update.effective_user is None:
        return
    user = update.effective_user
    message_text = update.effective_message.text

    print(f"El usuario {user.first_name} (id: {user.id}) ha enviado un mensaje.")

    if message_text is None:
        return

    message_detected_urls = re.findall(r"(https?://[^\s]+)", message_text)
    message_detected_urls = set(message_detected_urls)

    # Si la URL parseada no tiene hostname, buscar entidades de tipo URL
    if update.effective_message and update.effective_message.entities:
        for entity in update.effective_message.entities:
            if entity.type.lower() == "url":
                # Extraer la URL de la entidad
                entity_url = message_text[entity.offset : entity.offset + entity.length]
                if "http://" not in entity_url and "https://" not in entity_url:
                    entity_url = "http://" + entity_url

                # Comprobar si la URL es válida
                try:
                    _url = urlparse(entity_url)
                    if (
                        not _url.scheme
                        or not _url.netloc
                        or not _url.path
                        or not _url.hostname
                    ):
                        raise ValueError("URL inválida")
                    message_detected_urls.add(entity_url)
                except ValueError:
                    logger.error(f"URL inválida: {entity_url}")
                    continue

                internal_entity_url = entity.url
                # logger.info(f"El usuario {user.first_name} ha enviado una entidad URL. Entidad URL: {internal_entity_url} {entity_url} {entity.type}")
                if internal_entity_url is not None:
                    # Comprobar si la URL es válida
                    try:
                        _url = urlparse(internal_entity_url)
                        if (
                            not _url.scheme
                            or not _url.netloc
                            or not _url.path
                            or not _url.hostname
                        ):
                            raise ValueError("URL inválida")
                    except ValueError:
                        logger.error(f"URL inválida: {internal_entity_url}")
                        continue
                    logger.info(f"URL extraída: {internal_entity_url}")
                    message_detected_urls.add(internal_entity_url)

    logger.info(
        f"Usuario {user.first_name} ha enviado un mensaje con enlaces: {message_detected_urls}"
    )

    # Comprobar si el mensaje contiene un enlace.
    async def check_urls(msg_url: str = "") -> None:
        try:
            url = urlparse(msg_url)
            url_link = url.geturl()
            if update.effective_message is None:
                return
            if url.hostname is None:
                return
                # Descargar el post de Instagram
                media_contents = await download_instagram_post(url_link)

                if media_contents:
                    # Enviar cada archivo como respuesta al mensaje original
                    for filename, content, mime_type in media_contents:
                        file_obj = BytesIO(content)
                        file_obj.name = filename

                        if mime_type.startswith("image/"):
                            await update.effective_message.reply_photo(
                                photo=file_obj,
                                caption=f"Contenido descargado de Instagram",
                            )
                        elif mime_type.startswith("video/"):
                            await update.effective_message.reply_video(
                                video=file_obj,
                                caption=f"Contenido descargado de Instagram",
                            )

                else:
                    await update.effective_message.reply_text(
                        "Lo siento, no pude descargar el contenido de Instagram."
                    )



                    # Borrar el mensaje original
                    await update.effective_message.delete()

                    # await update.effective_message.reply_text(
                    #     "No se pueden enviar enlaces de Telegram en este grupo."
                    # )

            telegram_domains = ["bots.pb2a.com", "deepnude.us", "fknbot.com"]
            if url.hostname in telegram_domains:
                if not isAdmin(user.id):
                    if update.effective_chat is None:
                        return
                    if update.effective_message is None:
                        return
                    await update.effective_message.delete()
                    await update.effective_chat.ban_member(
                        user.id, until_date=None, revoke_messages=False  # type: ignore
                    )

        except:
            pass

    for msg_url in message_detected_urls:
        await check_urls(msg_url)

    # Palabras baneadas
    palabras_baneadas = [
        "menor",
        "caldo de pollo",
        "CP",
        "menores",
        "menor de edad",

        "ex",
    ]
    for palabra in palabras_baneadas:
        if (
            palabra.lower()
            in message_text.lower()
            .replace("?", " ")
            .replace(".", " ")
            .replace(",", " ")
            .split()
        ):
            # encoded_text = f"WRD: {palabra} UID: {user.id} UNM: {user.username}"
            # Codificar el texto en base64
            # encoded_b64 = base64.b64encode(encoded_text.encode()).decode()

            # Borrar el mensaje original
            # if update.effective_chat is not None:
            #     try:
            #         await update.effective_chat.delete_message(update.effective_message.message_id)
            #         logger.info(f"Mensaje con palabra prohibida borrado: {palabra}")
            #     except Exception as e:
            #         logger.error(f"No se pudo borrar el mensaje: {e}")

            # Enviar la notificación
            # await update.effective_message.reply_text(
            #     f"Ojo que te cojo\. @diidinaeg \n `@{bot_username} {encoded_b64}`",  # type: ignore
            #     parse_mode=ParseMode.MARKDOWN_V2,
            #     disable_web_page_preview=True,
            # )

            # Get message link
            if update.effective_chat is None or update.effective_message is None:
                return
            message_group_id = int(str(update.effective_chat.id).replace("-100", ""))
            topic_id = ""
            if update.effective_chat.is_forum:
                logger.info(f"El grupo es un foro. ID: {message_group_id} topic_id: {update.effective_message.message_thread_id}")
                topic_id = f"/{update.effective_message.message_thread_id}"
            message_link = f"https://t.me/c/{message_group_id}{topic_id}/{update.effective_message.message_id}"
            topic_title = update.effective_chat.title if update.effective_chat else "Grupo"
            user_mention = user.mention_markdown_v2() if user.username else user.first_name
            alert_text = f"\[ALERTA\] Palabra prohibida detectada en el grupo {topic_title} por @{user.username} \({user.id} \- {user_mention}\)\n\nPalabra: `{palabra}`\n\nMensaje: `{message_text}`\n\n[Ver mensaje]({message_link})\n\n"
            logger.info(alert_text)
            fwd_message = await update.effective_message.forward(chat_id=ADMIN_CHAT_ID)
            await fwd_message.reply_text(text=alert_text, parse_mode=ParseMode.MARKDOWN_V2)
            logger.warning(
                f"El usuario {user.first_name} (id: {user.id} @{user.username}) ha enviado un mensaje que contiene una palabra prohibida: {palabra}."
            )
            return


async def callback_auto_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje automático usando el chat_id almacenado en job.data"""
    if context.job is None or context.job.chat_id is None:
        return
    chat_id = context.job.chat_id  # En v20+ se usa job.data en lugar de context
    # Enviar mensaje aleatorio de la lista MENSAJES_INTERVALOS
    mensaje = random.choice(MENSAJES_INTERVALOS).replace(".", "\.").replace("-", "\-").replace("(", "\(").replace(")", "\)").replace("_", "\_").replace("[", "\[").replace("]", "\]").replace("!", "\!")  # type: ignore
    await context.bot.send_message(chat_id=chat_id, text=MENSAJES_INTERVALOS[0])


@restricted(reply=True, custom_message="Solo los admins pueden ejecutar esto tonto\.") # type: ignore
async def start_auto_messaging(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Inicia el envío de mensajes automáticos"""
    logger.info("Iniciando mensajes automáticos")
    if (
        update.effective_chat is None
        or update.effective_message is None
        or context.job_queue is None
    ):
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


@restricted(reply=True, custom_message="Solo los admins pueden ejecutar esto tonto\.")
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



# @restricted(reply=True, custom_message="Solo los admins pueden ejecutar esto tonto\.")
# async def decode_base64(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Decodifica un texto en base64"""
#     if update.effective_user is None or update.message is None:
#         return
#     if context.args is None or len(context.args) == 0:
#         await update.message.reply_text("Uso: /decode [texto_base64]")
#         return

#     encoded_text = " ".join(context.args)
#     try:
#         decoded_text = base64.b64decode(encoded_text.encode()).decode("utf-8")
#         await update.message.reply_text(
#             f"Texto decodificado:\n`{decoded_text}`", parse_mode=ParseMode.MARKDOWN_V2
#         )
#     except Exception as e:
#         await update.message.reply_text(f"Error al decodificar: {str(e)}")


@restricted(reply=True, custom_message="Solo los admins pueden ejecutar esto tonto\.")
async def inline_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Maneja consultas inline para decodificar base64"""
    if update.inline_query is None or update.inline_query.query is None:
        return
    query = update.inline_query.query

    if not query:
        return

    results = []
    try:
        # Intentar decodificar el texto en base64
        decoded_text = base64.b64decode(query.encode()).decode("utf-8")
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Decodificar Base64",
                input_message_content=InputTextMessageContent(
                    f"\+20€", parse_mode=ParseMode.MARKDOWN_V2  # type: ignore
                ),
                description=(
                    f"Resultado: {decoded_text[:15]}..."
                    if len(decoded_text) > 50
                    else f"Resultado: {decoded_text}"
                ),
            )
        )
    except Exception as e:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Error al decodificar",
                input_message_content=InputTextMessageContent(
                    "No se pudo decodificar el texto en base64."
                ),
                description="El texto proporcionado no es un base64 válido.",
            )
        )

    await update.inline_query.answer(results, is_personal=True, cache_time=0)

async def chatid_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Maneja el comando /chatid"""
    if update.effective_chat is None or update.effective_message is None:
        return

    chat_id = update.effective_chat.id
    message = f"El ID del chat es: `{chat_id}`"
    await update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)

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
    application.add_handler(CommandHandler("ban", ban_handler))
    application.add_handler(CommandHandler("unban", unban_handler))
    application.add_handler(CommandHandler("unrestrict", unrestrict_handler))
    application.add_handler(CommandHandler("chatid", chatid_handler))
    application.add_handler(
        ChatMemberHandler(greet_new_member, ChatMemberHandler.CHAT_MEMBER)
    )  # Se completa el ChatMemberHandler para saludar a nuevos usuarios

    # Añadir manejador para consultas inline
    application.add_handler(InlineQueryHandler(inline_query_handler))

    # Run the bot until the user presses Ctrl-C
    application.add_handler(CommandHandler("auto", start_auto_messaging))
    application.add_handler(CommandHandler("stop", stop_notify))
    application.add_handler(MessageHandler(filters.ALL, all_messages_handler))

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
