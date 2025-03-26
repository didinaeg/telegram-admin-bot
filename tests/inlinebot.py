#!/usr/bin/env python

# pylint: disable=unused-argument

# This program is dedicated to the public domain under the CC0 license.

"""
Simple bot that allows downloading videos through URL.
Send /download [url] to start the download process.

Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
from typing import Any, Dict, Optional
import os
import asyncio
from urllib.parse import urlparse

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Message
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Estado para la conversación de descarga
DOWNLOAD_CHOOSING, DOWNLOADING = range(2)

# Variable para almacenar las descargas activas por usuario
active_downloads = {}

# Manejador inicial para el comando download (fuera del ConversationHandler)
async def download_command_initial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the initial /download command and create an inline button to start the conversation"""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Por favor, proporciona una URL válida: /download [url]")
        return
    
    url = context.args[0]
    
    # Crear un mensaje con un botón para iniciar la conversación
    buttons = [
        [InlineKeyboardButton(text="Iniciar descarga", callback_data=f"start_download:{url}")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    await update.message.reply_text(
        f"Haz clic en el botón para iniciar el proceso de descarga para:\n{url}", 
        reply_markup=keyboard
    )

# Funciones para el ConversationHandler (todas manejando callbacks)
async def download_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start download conversation from callback"""
    query = update.callback_query
    await query.answer()
    
    # Extraer la URL del callback_data
    url = query.data.split(':', 1)[1]
    user_id = update.effective_user.id
    
    # Verificar si hay una descarga activa para este usuario y cancelarla
    if user_id in active_downloads and active_downloads[user_id]['active']:
        active_downloads[user_id]['active'] = False
        if 'message' in active_downloads[user_id]:
            try:
                await active_downloads[user_id]['message'].edit_text("Descarga cancelada: se solicitó una nueva descarga.")
            except Exception:
                pass
    
    # Guardar URL en contexto
    context.user_data['download_url'] = url
    
    # Inicializar o actualizar el registro de descargas para este usuario
    active_downloads[user_id] = {
        'url': url,
        'active': False,
        'message': None
    }
    
    buttons = [
        [
            InlineKeyboardButton(text="SI", callback_data="download_yes"),
            InlineKeyboardButton(text="NO", callback_data="download_no"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(
        f"¿Quieres descargar el video de esta URL?\n{url}", 
        reply_markup=keyboard
    )
    
    return DOWNLOAD_CHOOSING

async def stop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation from callback query"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Verificar si hay una descarga activa y cancelarla
    if user_id in active_downloads and active_downloads[user_id]['active']:
        active_downloads[user_id]['active'] = False
        if 'message' in active_downloads[user_id]:
            try:
                await active_downloads[user_id]['message'].edit_text("Descarga cancelada por el usuario.")
            except Exception:
                pass
    
    await query.edit_message_text("Operación cancelada.")
    return ConversationHandler.END

# Función para detener la conversación mediante comando (fuera del ConversationHandler)
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle stop command from outside the conversation"""
    user_id = update.effective_user.id
    
    # Verificar si hay una descarga activa y cancelarla
    if user_id in active_downloads and active_downloads[user_id]['active']:
        active_downloads[user_id]['active'] = False
        if 'message' in active_downloads[user_id]:
            try:
                await active_downloads[user_id]['message'].edit_text("Descarga cancelada por el usuario.")
            except Exception:
                pass
    
    await update.message.reply_text("Todas las operaciones canceladas.")

async def download_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user selecting 'SI' for download"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    url = context.user_data.get('download_url')
    message = await query.edit_message_text(f"Iniciando la descarga de: {url}\nProgreso: 0%")
    
    # Marcar esta descarga como activa
    if user_id in active_downloads:
        active_downloads[user_id]['active'] = True
        active_downloads[user_id]['message'] = message
    
    # Iniciar la descarga con simulación de progreso
    await download_video(context, url, message, user_id)
    
    return ConversationHandler.END

async def download_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user selecting 'NO' for download"""
    query = update.callback_query
    if not query:
        return ConversationHandler.END

    await query.answer()
    
    user_id = update.effective_user.id
    
    # Eliminar la descarga pendiente
    if user_id in active_downloads:
        active_downloads.pop(user_id, None)
    
    await query.edit_message_text("Descarga cancelada.")
    
    return ConversationHandler.END

async def download_video(context: ContextTypes.DEFAULT_TYPE, url: str, message: Message, user_id: int) -> None:
    """Simulate downloading the video and update progress"""
    try:
        # Simulamos la descarga con porcentajes
        for progress in range(0, 101, 10):
            # Verificar si la descarga fue cancelada
            if user_id not in active_downloads or not active_downloads[user_id]['active']:
                return
                
            await message.edit_text(f"Descargando: {url}\nProgreso: {progress}%")
            await asyncio.sleep(1)  # Simular tiempo de descarga
        
        # Una vez completada la descarga, enviamos el video
        # En un caso real, aquí enviaríamos el archivo descargado
        if user_id in active_downloads and active_downloads[user_id]['active']:
            await message.delete()
            await context.bot.send_message(
                chat_id=message.chat_id,
                text="¡Video descargado exitosamente! En una implementación real, aquí enviaríamos el archivo de video."
            )
            # Marcar la descarga como completa
            active_downloads[user_id]['active'] = False
    
    except Exception as e:
        if user_id in active_downloads and active_downloads[user_id]['active']:
            await message.edit_text(f"Error durante la descarga: {str(e)}")
            active_downloads[user_id]['active'] = False

# Función para manejar el timeout de la conversación
async def conversation_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout"""
    # Obtener el mensaje original de la conversación
    user_id = context.user_id if hasattr(context, 'user_id') else None
    
    # Si hay información de usuario en el contexto del timeout
    if user_id and user_id in active_downloads:
        # Marcar la descarga como inactiva
        active_downloads[user_id]['active'] = False
        
        # Intentar editar el mensaje si existe
        if 'message' in active_downloads[user_id] and active_downloads[user_id]['message']:
            try:
                await active_downloads[user_id]['message'].edit_text("La operación de descarga fue cancelada por timeout.")
            except Exception as e:
                logger.error(f"Error al actualizar mensaje de timeout: {e}")
    
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("7512065541:AAEnfNlaSNSGi1rs9M0xn_65vsGBYmZHTCE").build()

    # Handler para el comando inicial
    application.add_handler(CommandHandler("download", download_command_initial))
    application.add_handler(CommandHandler("stop", stop_command))
    
    # Conversación para descarga de videos (ahora todos son CallbackQueryHandler)
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
        conversation_timeout=10,
        conversation_timeout_handler=conversation_timeout,
        block=False,
        per_message=True,
        per_user=False,
        per_chat=True,
    )
    
    application.add_handler(download_conv)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()