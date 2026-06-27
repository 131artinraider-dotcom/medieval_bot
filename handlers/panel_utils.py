# handlers/panel_utils.py
# سیستم قفل پنل - per-message
# هر پیام یه owner داره. فقط owner میتونه دکمه‌هاش رو بزنه.

from telegram import Update
from telegram.ext import ContextTypes


def _key(message_id: int) -> str:
    return f"panel_{message_id}"


async def check_panel_ownership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    بررسی مالکیت پنل.
    اگه کاربر owner نبود، پیام خطا میده و False برمیگردونه.
    """
    query = update.callback_query
    user_id = query.from_user.id
    message_id = query.message.message_id

    key = _key(message_id)
    owner_id = context.bot_data.get(key)

    if owner_id is None:
        # پنل قدیمیه و ثبت نشده - اجازه بده رد بشه
        return True

    if owner_id != user_id:
        await query.answer("❌ این پنل متعلق به شما نیست!", show_alert=True)
        return False

    return True


async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    ثبت مالکیت پنل برای این message_id.
    اگه یه نفر دیگه‌ای owner باشه، False برمیگردونه.
    """
    query = update.callback_query
    user_id = query.from_user.id
    message_id = query.message.message_id

    key = _key(message_id)
    owner_id = context.bot_data.get(key)

    if owner_id is not None and owner_id != user_id:
        await query.answer("❌ این پنل متعلق به شما نیست!", show_alert=True)
        return False

    context.bot_data[key] = user_id
    return True


async def clear_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن مالکیت پنل بعد از بسته شدن."""
    query = update.callback_query
    message_id = query.message.message_id
    key = _key(message_id)
    context.bot_data.pop(key, None)


def register_panel(message_id: int, user_id: int, context) -> None:
    """
    ثبت owner برای پنلی که تازه ارسال شده.
    بعد از send/reply_text صدا زده میشه.
    """
    key = _key(message_id)
    context.bot_data[key] = user_id
