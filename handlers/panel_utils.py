# handlers/panel_utils.py
import time
from telegram import Update
from telegram.ext import ContextTypes


def _key(message_id: int) -> str:
    return f"panel_{message_id}"


def register_panel(message_id: int, user_id: int, context) -> None:
    """ثبت owner برای پنل با timestamp"""
    key = _key(message_id)
    context.bot_data[key] = {"uid": user_id, "ts": time.time()}


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
        await query.answer("⏰ این پنل منقضی شده! دوباره کامند بزن.", show_alert=True)
        try:
            await query.delete_message()
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
