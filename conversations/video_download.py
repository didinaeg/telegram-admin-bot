# Variable para almacenar las descargas activas por usuario
import asyncio
import os
import tempfile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from estados import DOWNLOAD_CHOOSING
import logging
import traceback

logger = logging.getLogger(__name__)


active_downloads = {}

# Funciones para el ConversationHandler (todas manejando callbacks)
async def download_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start download conversation from callback"""
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    await query.answer()
    
    # Extraer la URL del callback_data
    if not query.data or ':' not in query.data:
        await query.edit_message_text("No se proporcionó una URL válida.")
        return ConversationHandler.END
    url = query.data.split(':', 1)[1]
    
    if not update.effective_user:
        await query.edit_message_text("No se pudo identificar al usuario.")
        return ConversationHandler.END
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
    if not context.user_data:
        try:
            context.user_data = {}
        except Exception as e:
            logger.error(f"Error initializing user_data: {e}")
    context.user_data['download_url'] = url # type: ignore
    
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
    if not query:
        return ConversationHandler.END
    await query.answer()
    
    if not update.effective_user:   
        await query.edit_message_text("No se pudo identificar al usuario.")
        return ConversationHandler.END
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
    if not update.effective_user:
        await query.edit_message_text("No se pudo identificar al usuario.")
        return ConversationHandler.END
    user_id = update.effective_user.id
    # Verificar si user_data existe y si contiene la URL
    if not context.user_data or 'download_url' not in context.user_data:
        await query.edit_message_text("No se encontró la URL para descargar.")
        return ConversationHandler.END
    url = context.user_data['download_url']
    message = await query.edit_message_text(f"Iniciando la descarga de: {url}\nProgreso: 0%")
    
    # Marcar esta descarga como activa
    if user_id in active_downloads:
        active_downloads[user_id]['active'] = True
        active_downloads[user_id]['message'] = message
    
    # Iniciar la descarga con simulación de progreso   
    await download_video(context, url, message, user_id) # type: ignore
    
    return ConversationHandler.END

async def download_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user selecting 'NO' for download"""
    query = update.callback_query
    if not query:
        return ConversationHandler.END

    await query.answer()
    if not update.effective_user:   
        await query.edit_message_text("No se pudo identificar al usuario.")
        return ConversationHandler.END
    user_id = update.effective_user.id
    
    # Eliminar la descarga pendiente
    if user_id in active_downloads:
        active_downloads.pop(user_id, None)
    
    await query.edit_message_text("Descarga cancelada.")
    
    return ConversationHandler.END

async def download_video(context: ContextTypes.DEFAULT_TYPE, url: str, message: Message, user_id: int) -> None:
    """Download the video using yt_dlp and send it to the user"""
    try:
        # Crear un directorio temporal para guardar el video
        with tempfile.TemporaryDirectory() as temp_dir:
            # Configurar opciones de descarga
            ydl_opts = {
                'format': 'best[height<=720]',  # Limitar la calidad a 720p para que no sea muy grande
                'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                'progress_hooks': [],  # Lo configuraremos más abajo
                'noplaylist': True,    # Solo descargar el video, no la playlist
            }
            
            # Variable para almacenar la información del video y la ruta del archivo
            video_info = {'title': None, 'duration': None}
            video_path = None
            last_percent = 0
            
            # Hook para mostrar el progreso
            def progress_hook(progress):
                nonlocal last_percent
                nonlocal video_info
                nonlocal video_path
                if progress['status'] == 'downloading':
                    # Extraer el porcentaje de la descarga
                    if '_percent_str' in progress:
                        percent_str = progress['_percent_str'].strip()
                        if percent_str.endswith('%'):
                            try:
                                percent = int(float(percent_str[:-1]))
                                # Solo actualizar si el porcentaje cambió significativamente
                                if percent >= last_percent + 10 or percent == 100:
                                    last_percent = percent
                                    logger.info(f"[{percent}%] {video_info['title']}")
                                    asyncio.create_task(
                                        message.edit_text(
                                            f"Descargando: {video_info['title']}\n"
                                            f"Duración: {video_info['duration']} segundos\n"
                                            f"Progreso: {percent}%"
                                        )
                                    )
                            except ValueError:
                                pass
                elif progress['status'] == 'finished':
                    video_path = progress['filename']
                    logger.info(f"Descarga completada at: {video_path}")
                    asyncio.create_task(
                        message.edit_text(
                            f"Descarga completada: {video_info['title']}\n"
                            f"Preparando para enviar..."
                        )
                    )
            
            # Agregar el hook a las opciones
            ydl_opts['progress_hooks'].append(progress_hook)
            
            # Primero, extraer información sin descargar
            with YoutubeDL(ydl_opts) as ydl:
                # Verificar si la descarga fue cancelada
                if user_id not in active_downloads or not active_downloads[user_id]['active']:
                    return
                    
                # Obtener información del video
                info = ydl.extract_info(url, download=False)
                if not info:
                    await message.edit_text(f"No se pudo obtener información del video: {url}")
                    active_downloads[user_id]['active'] = False
                    return
                
                video_info['title'] = info.get('title', 'Video desconocido')
                video_info['duration'] = info.get('duration', 'desconocida')
                
                await message.edit_text(
                    f"Descargando: {video_info['title']}\n"
                    f"Duración: {video_info['duration']} segundos\n"
                    f"Progreso: 0%"
                )
                logger.info(f"Descargando: {video_info['title']} ({video_info['duration']} segundos)")

                # Verificar si la descarga fue cancelada
                if user_id not in active_downloads or not active_downloads[user_id]['active']:
                    return
                
                ydl.download([url])
                logger.info(f"Descarga completada: {video_info['title']}")
            
            # Verificar si tenemos la ruta y si la descarga no fue cancelada
            if video_path and os.path.exists(video_path) and user_id in active_downloads and active_downloads[user_id]['active']:
                # Enviar el video
                logger.info(f"Enviando video: {video_info['title']}")
                await message.edit_text(f"Enviando video: {video_info['title']}")
                
                # Usar with para asegurar que el archivo se cierre correctamente
                with open(video_path, 'rb') as video_file:
                    await context.bot.send_document(
                        chat_id=message.chat_id, 
                        document=video_file,
                        caption=f"Título: {video_info['title']}"
                    )
                # Eliminar el mensaje de progreso
                await message.delete()
                # Marcar la descarga como completa
                active_downloads[user_id]['active'] = False


    
    except DownloadError as e:
        if user_id in active_downloads and active_downloads[user_id]['active']:
            logger.error(f"Error al descargar el video: {str(e)}")
            await message.edit_text(f"Error al descargar el video: {str(e)}")
            active_downloads[user_id]['active'] = False
    except Exception as e:
        traceback.print_exc()
        if user_id in active_downloads and active_downloads[user_id]['active']:
            logger.error(f"Error durante la descarga: {str(e)}")
            await message.edit_text(f"Error durante la descarga: {str(e)}")
            active_downloads[user_id]['active'] = False
