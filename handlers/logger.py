# handlers/logger.py
"""
ذخیره خودکار همه پیام‌های گروه (گروه/سوپرگروه) در دیتابیس.
این هندلر مستقل از هندلر اصلی کامندهاست؛ هر پیام متنی گروه رو
بدون دخالت در روند بازی، فقط لاگ می‌کنه.
"""
from telegram import Update
from telegram.ext import ContextTypes
from database import save_chat_message


async def log_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره پیام‌های متنی گروه/سوپرگروه در جدول chat_messages"""
    message = update.message
    if not message or not message.text:
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return  # فقط گروه‌ها رو لاگ کن، نه پی‌وی

    user = update.effective_user
    if not user:
        return

    full_name = user.full_name or ""
    username = user.username or ""

    try:
        await save_chat_message(
            chat_id=chat.id,
            chat_title=chat.title or "",
            user_id=user.id,
            username=username,
            full_name=full_name,
            message_text=message.text,
            message_id=message.message_id
        )
    except Exception as e:
        # خطای ذخیره پیام نباید کل بات رو متوقف کنه
        print(f"⚠️ خطا در ذخیره پیام گروه: {e}")
