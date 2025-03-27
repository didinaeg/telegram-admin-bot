
# Variable para almacenar las descargas activas por usuario
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from estados import DOWNLOAD_CHOOSING


active_downloads = {}

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
    if not update.effective_user or not update.message:
        return
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
    if not query:
        return ConversationHandler.END
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
