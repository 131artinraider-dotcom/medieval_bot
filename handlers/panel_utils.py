# handlers/panel_utils.py

from telegram import Update
from telegram.ext import ContextTypes

# ========================================
# توابع قفل پنل
# ========================================

async def ensure_panel_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    اطمینان از دسترسی کاربر به پنل
    اگر پنل وجود نداشته باشه، ثبت میکنه
    اگر پنل وجود داشته باشه و مال خودش باشه، اجازه میده
    اگر پنل وجود داشته باشه و مال خودش نباشه، رد میکنه
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}"
    
    # ===== اگر پنلی برای این چت ثبت نشده =====
    if key not in context.chat_data:
        # ثبت پنل جدید برای این کاربر
        context.chat_data[key] = user_id
        return True
    
    # ===== پنل وجود داره، مالک رو چک کن =====
    owner_id = context.chat_data[key]
    
    # ===== اگر کاربر فعلی مالک نیست =====
    if owner_id != user_id:
        await query.answer("❌ این پنل متعلق به شما نیست!", show_alert=True)
        return False
    
    # ===== مالک خودشه =====
    return True

async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    ثبت مالکیت پنل برای کاربر
    فقط یک پنل در هر گروه میتونه فعال باشه
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}"
    
    # ===== چک کن که آیا پنل دیگه‌ای فعال هست =====
    if key in context.chat_data:
        owner_id = context.chat_data[key]
        if owner_id != user_id:
            await query.answer("❌ یک پنل دیگر در این گروه باز است! لطفاً صبر کنید.", show_alert=True)
            return False
    
    # ===== ثبت پنل جدید =====
    context.chat_data[key] = user_id
    return True

async def clear_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن مالکیت پنل کاربر"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}"
    
    # ===== فقط اگه مالک باشه میتونه پنل رو ببنده =====
    if key in context.chat_data and context.chat_data[key] == user_id:
        context.chat_data.pop(key, None)

