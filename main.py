from typing import Optional
from telegram import ChatMember, ChatMemberUpdated, Update
from telegram.ext import Application, CommandHandler, CallbackContext, ChatMemberHandler
from telegram.constants import ParseMode

from messages import RULES_MESSAGE

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

def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[tuple[bool, bool]]:

    """Toma una instancia de ChatMemberUpdated y extrae si el 'old_chat_member' era miembro
    del chat y si el 'new_chat_member' es miembro del chat. Devuelve None, si
    el estado no cambió.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)

    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)


    return was_member, is_member

# Función para manejar el comando /start
async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    logger.info(f"El usuario {user.first_name} ha iniciado una conversación.")
    message = (
        f"Hola, [{user.first_name}](tg://user?id={user.id}) soy Manolito,\n"
        "estoy aquí para ayudarte con la gestión de tu bar\n"
        "\¿qué necitas\?"
        
    )
    await update.message.reply_text(message, parse_mode="MarkdownV2")

async def greet_new_member(update: Update, context: CallbackContext) -> None:
    result = extract_status_change(update.chat_member)
    if result is None:
        logger.info("No se detectó un cambio en el estado del miembro.")
        return

    was_member, is_member = result
    cause_name = update.chat_member.from_user.mention_markdown_v2()
    member_name = update.chat_member.new_chat_member.user.name
    member_name_mention = update.chat_member.new_chat_member.user.mention_markdown_v2()
    member_id = update.chat_member.new_chat_member.user.id
    logger.info(f"El estado del miembro {member_name} (id: {member_id}) ha cambiado de {was_member} a {is_member}. Causado por {cause_name}.")
    # Saludar si el usuario pasó de no ser miembro a ser miembro
    if not was_member and is_member:
        logger.info(f"Saludando a {member_name} por unirse al grupo.")
        message = (
            f"¡Bienvenido al Bar de Manolo {member_name_mention}\!\n"
            "Para poder ser aceptado en el grupo envía lo siguiente:\n"
            "\- Dirección\n"
            "\- Objetos de valor y dónde los guarda\n"
            "\- Tipo sanguíneo\n"
            "No nos hacemos responsables de daños o perjuicios hacia su propiedad privada \(por favor consulta las /rules\)"
        )
        await update.effective_chat.send_message(
            message,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    elif was_member and not is_member:
        logger.warning(f"Despidiendo a {member_name} por salir del grupo.")

async def rules(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_text(RULES_MESSAGE, parse_mode=ParseMode.MARKDOWN_V2)

def main() -> None:
    # Reemplaza 'YOUR_TOKEN' con el token de tu bot
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    

    # Añadir manejador para el comando /start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(ChatMemberHandler(greet_new_member, ChatMemberHandler.CHAT_MEMBER))  # Se completa el ChatMemberHandler para saludar a nuevos usuarios

    # Run the bot until the user presses Ctrl-C

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()