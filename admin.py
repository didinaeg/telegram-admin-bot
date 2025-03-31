from telegram import Update
from utils import extract_status_change, isAdmin, restricted
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
import logging 

logger = logging.getLogger(__name__)

@restricted
async def ban_handler(update: Update, context: CallbackContext) -> None:
    if update.effective_chat is None:
        return
    if update.effective_message is None:
        return
    if update.effective_message.reply_to_message is None:
        await update.effective_message.reply_text(
            "Este comando necesita ser respondido a un mensaje"
        )
        return

    if update.effective_user is None:
        return

    message_user = update.effective_user

    reply_message = update.effective_message.reply_to_message
    if reply_message.from_user is None:
        return
    target_user = reply_message.from_user

    if not isAdmin(message_user.id):
        await update.effective_message.reply_text("solo los admins pueden banear.")
        return
    
    if isAdmin(target_user.id):
        await update.effective_message.reply_text("No puedes banear a un admin.")
        return

    # ban the user
    await update.effective_chat.ban_member(
        target_user.id,
        until_date=None,  # type: ignore
        revoke_messages=False
    )
    await update.effective_message.reply_text(
        f"Ban {target_user.mention_markdown_v2()}",
        parse_mode=ParseMode.MARKDOWN_V2
    )
    logger.info(f"Banned user {target_user.id} from chat {update.effective_chat.id}")

@restricted
async def unban_handler(update: Update, context: CallbackContext) -> None:
    if update.effective_chat is None:
        return
    if update.effective_message is None:
        return
    if update.effective_message.reply_to_message is None:
        await update.effective_message.reply_text(
            "Este comando necesita ser respondido a un mensaje"
        )
        return
    
    if update.effective_user is None:
        return
    
    message_user = update.effective_user
    reply_message = update.effective_message.reply_to_message
    if reply_message.from_user is None:
        return
    target_user = reply_message.from_user
    if not isAdmin(message_user.id):
        await update.effective_message.reply_text("solo los admins pueden desbanear.")
        return
    
    if isAdmin(target_user.id):
        await update.effective_message.reply_text("No puedes desbanear a un admin.")
        return
    
    # unban the user
    await update.effective_chat.unban_member(
        target_user.id,
        only_if_banned=True
    )
    await update.effective_message.reply_text(
        f"Desbaneado {target_user.mention_markdown_v2()}",
        parse_mode=ParseMode.MARKDOWN_V2
    )
    logger.info(f"Unbanned user {target_user.id} from chat {update.effective_chat.id}")