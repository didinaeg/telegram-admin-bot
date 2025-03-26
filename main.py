from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, ChatMemberHandler

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
async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    logger.info(f"El usuario {user.first_name} ha iniciado una conversación.")
    message = (
        f"¡Bienvenido, [{user.first_name}](tg://user?id={user.id})\! al Bar de Manolo\n"
        "Para poder ser aceptado en el grupo envía lo siguiente:\n"
        "\- Dirección\n"
        "\- Objetos de valor y dónde los guarda\n"
        "\- Tipo sanguíneo\n"
        "No nos hacemos responsables de daños o perjuicios hacia su propiedad privada \(por favor consultar\)"
    )
    await update.message.reply_text(message, parse_mode="MarkdownV2")

async def greet_new_member(update: Update, context: CallbackContext) -> None:
    result = update.chat_member
    # Saludar si el usuario pasó de no ser miembro a ser miembro
    if result.new_chat_member.status == "member" and result.old_chat_member.status not in ["member", "administrator", "creator"]:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"¡Bienvenido, {result.new_chat_member.user.first_name}! al Bar de Manolo, para poder ser aceptado en el grupo envie lo siguiente: /n -Dirección /n -objetos de valor y donde los guarda /n  -tipo sanguíneo / n No nos hacemos responsables de daños o perjuicios hacia su propiedad privada (porfavor consultar  )")

def main() -> None:
    # Reemplaza 'YOUR_TOKEN' con el token de tu bot
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    

    # Añadir manejador para el comando /start
    application.add_handler(CommandHandler("start", start))
    application.add_handler(ChatMemberHandler(greet_new_member))  # Se completa el ChatMemberHandler para saludar a nuevos usuarios

    # Run the bot until the user presses Ctrl-C

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()