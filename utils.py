from typing import Optional

from telegram import ChatMember, ChatMemberUpdated


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

