# handlers/panel_utils.py
import time
from telegram import Update
from telegram.ext import ContextTypes


def _key(message_id: int) -> str:
    return f"panel_{message_id}"


def register_panel(message_id: int, user_id: int, context, chat_id: int = None) -> None:
    """ثبت owner برای پنل با timestamp"""
    key = _key(message_id)
    context.bot_data[key] = {"uid": user_id, "ts": time.time(), "chat_id": chat_id}


async def check_panel_ownership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """بررسی مالکیت و انقضای پنل"""
    query = update.callback_query
    user_id = query.from_user.id
    message_id = query.message.message_id
    key = _key(message_id)
    data = context.bot_data.get(key)

    if data is None:
        return True  # پنل قدیمی - اجازه بده

    # چک timeout 10 دقیقه
    if time.time() - data.get("ts", 0) > 600:
        context.bot_data.pop(key, None)
        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            await query.answer()
        except Exception:
            pass
        return False

    if data.get("uid") != user_id:
        await query.answer("❌ این پنل متعلق به شما نیست!", show_alert=True)
        return False

    return True


async def clear_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن مالکیت پنل"""
    query = update.callback_query
    message_id = query.message.message_id
    context.bot_data.pop(_key(message_id), None)
