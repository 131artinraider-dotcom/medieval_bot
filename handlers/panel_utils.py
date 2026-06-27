# handlers/panel_utils.py

from telegram import Update
from telegram.ext import ContextTypes

# ========================================
# توابع قفل پنل - نسخه ساده با context.chat_data
# ========================================

async def check_panel_ownership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    بررسی مالکیت پنل - فقط مالک پنل میتونه دکمه‌هاش رو بزنه
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}"
    
    # ===== اگر پنلی برای این چت ثبت نشده =====
    if key not in context.chat_data:
        await query.answer("❌ هیچ پنل فعالی در این گروه وجود ندارد! لطفاً پنل رو دوباره باز کن.", show_alert=True)
        return False
    
    # ===== پنل وجود داره، مالک رو چک کن =====
    owner_id = context.chat_data[key]
    
    # ===== اگر کاربر فعلی مالک نیست =====
    if owner_id != user_id:
        await query.answer("❌ این پنل متعلق به شما نیست!", show_alert=True)
        return False
    
    return True

async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    ثبت مالکیت پنل برای کاربر
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}"
    
    # ===== اگر پنل دیگه‌ای فعال هست =====
    if key in context.chat_data:
        owner_id = context.chat_data[key]
        if owner_id != user_id:
            await query.answer("❌ یک پنل دیگر در این گروه باز است! لطفاً صبر کنید.", show_alert=True)
            return False
    
    # ===== ثبت پنل جدید =====
    context.chat_data[key] = user_id
    return True

async def clear_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن مالکیت پنل"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}"
    
    if key in context.chat_data and context.chat_data[key] == user_id:
        context.chat_data.pop(key, None)

