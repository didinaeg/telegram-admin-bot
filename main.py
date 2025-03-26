from typing import Optional
from telegram import ChatMember, ChatMemberUpdated, Update
from telegram.ext import Application, CommandHandler, CallbackContext, ChatMemberHandler , MessageHandler, filters
from telegram.constants import ParseMode
from urllib.parse import urlparse

from messages import RULES_MESSAGE
from utils import extract_status_change

import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)



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

async def all_messages_handler(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return
    message= update.message.text

    if message is None:
        return

    # Comprobar si el mensaje contiene un enlace.
    try:
        url = urlparse(message)
        # Check if the url a youtube link
        youtube_domains = ["www.youtube.com", "youtube.com", "youtu.be"]
        if url.hostname in youtube_domains:
            logger.info(f"El usuario {user.first_name} ha enviado un enlace de YouTube.")
            await update.message.reply_text("No se pueden enviar enlaces de YouTube en este grupo.")

        instagram_domains = ["www.instagram.com", "instagram.com"]
        if url.hostname in instagram_domains:
            logger.info(f"El usuario {user.first_name} ha enviado un enlace de Instagram.")
            await update.message.reply_text("No se pueden enviar enlaces de Instagram en este grupo.")

        tiktok_domains = ["www.tiktok.com", "tiktok.com"]
        if url.hostname in tiktok_domains:
            logger.info(f"El usuario {user.first_name} ha enviado un enlace de TikTok.")
            await update.message.reply_text("No se pueden enviar enlaces de TikTok en este grupo.")
    except:
        pass


def main() -> None:
    # Reemplaza 'YOUR_TOKEN' con el token de tu bot
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if TELEGRAM_BOT_TOKEN is None:
        logger.error(
            "No se encontró el token del bot en la variable de entorno TELEGRAM_BOT_TOKEN"
        )
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Añadir manejador para el comando /start
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("rules", rules_handler))
    application.add_handler(
        ChatMemberHandler(greet_new_member, ChatMemberHandler.CHAT_MEMBER)
    )  # Se completa el ChatMemberHandler para saludar a nuevos usuarios
    application.add_handler(MessageHandler(filters.ALL, all_messages_handler))
    # Run the bot until the user presses Ctrl-C

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
