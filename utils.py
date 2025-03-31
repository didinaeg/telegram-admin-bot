from typing import Optional
from uuid import uuid4
import logging

from telegram import ChatMember, ChatMemberUpdated, InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.constants import ParseMode

from functools import wraps

logger = logging.getLogger(__name__)

LIST_OF_ADMINS = [906631113]

def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        if update.effective_user is None:
            return
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print(f"Unauthorized access denied for {user_id}.")
            try:
                if update.inline_query is None or update.inline_query.query is None:
                    return
                query = update.inline_query.query
                
                if not query:
                    return

                user_mention = update.effective_user.mention_markdown_v2()
                results = []
                results.append(
                    InlineQueryResultArticle(
                        id=str(uuid4()),
                        title="Kitty",
                        input_message_content=InputTextMessageContent(
                            f"{user_mention} la chupa",
                            parse_mode=ParseMode.MARKDOWN_V2
                        ),
                        description=f"-20 creditos sociales"
                    )
                )
                await update.inline_query.answer(results, is_personal=True, cache_time=0)
            except Exception as e:
                logger.error(f"Error while handling inline query: {e}")
                return
            return
        return await func(update, context, *args, **kwargs)
    return wrapped



def extract_status_change(
    chat_member_update: ChatMemberUpdated,
) -> Optional[tuple[bool, bool]]:
    """Toma una instancia de ChatMemberUpdated y extrae si el 'old_chat_member' era miembro
    del chat y si el 'new_chat_member' es miembro del chat. Devuelve None, si
    el estado no cambió.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get(
        "is_member", (None, None)
    )

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

