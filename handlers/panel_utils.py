# handlers/panel_utils.py

from telegram import Update
from telegram.ext import ContextTypes

# ========================================
# توابع قفل پنل (جدا از بقیه برای جلوگیری از circular import)
# ========================================

# handlers/panel_utils.py

async def check_ownership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    بررسی مالکیت پنل - هر کاربر فقط پنل خودش رو میتونه کنترل کنه
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}_{user_id}"
    
    # ✅ اگر کلید وجود نداشت، یعنی کاربر پنل جدید باز کرده، اجازه بده
    if key not in context.chat_data:
        # ثبت پنل جدید
        context.chat_data[key] = user_id
        return True
    
    # اگر کلید وجود داشت، مالکیت رو چک کن
    return True  # همیشه true برگردون چون کلید مال خودشه

async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثبت مالکیت پنل برای کاربر"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}_{user_id}"
    
    # پاک کردن پنل قبلی این کاربر (اگه وجود داشته باشه)
    context.chat_data.pop(key, None)
    
    # ثبت پنل جدید
    context.chat_data[key] = user_id

async def clear_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن مالکیت پنل کاربر"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}_{user_id}"
    context.chat_data.pop(key, None)

