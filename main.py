from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, ChatMemberHandler

# Función para manejar el comando /start
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_text(f"¡Bienvenido, {user.first_name}! al Bar de Manolo, para poder ser aceptado en el grupo envie lo siguiente: /n -Dirección /n -objetos de valor y donde los guarda /n  -tipo sanguíneo / n No nos hacemos responsables de daños o perjuicios hacia su propiedad privada (porfavor consultar  )")

def greet_new_member(update: Update, context: CallbackContext) -> None:
    result = update.chat_member
    # Saludar si el usuario pasó de no ser miembro a ser miembro
    if result.new_chat_member.status == "member" and result.old_chat_member.status not in ["member", "administrator", "creator"]:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"¡Bienvenido, {result.new_chat_member.user.first_name}! al Bar de Manolo, para poder ser aceptado en el grupo envie lo siguiente: /n -Dirección /n -objetos de valor y donde los guarda /n  -tipo sanguíneo / n No nos hacemos responsables de daños o perjuicios hacia su propiedad privada (porfavor consultar  )")

def main() -> None:
    # Reemplaza 'YOUR_TOKEN' con el token de tu bot
    updater = Updater("")

    dispatcher = updater.dispatcher
    

    # Añadir manejador para el comando /start
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(ChatMemberHandler(greet_new_member))  # Se completa el ChatMemberHandler para saludar a nuevos usuarios

    # Iniciar el bot
    updater.start_polling()

    # Mantener el bot corriendo hasta que se detenga manualmente
    updater.idle()

if __name__ == '__main__':
    main()