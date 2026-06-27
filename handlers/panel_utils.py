# handlers/panel_utils.py

from telegram import Update
from telegram.ext import ContextTypes

# ========================================
# توابع قفل پنل - فقط یک پنل در هر گروه فعال باشه
# ========================================

async def check_ownership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    بررسی مالکیت پنل - فقط مالک پنل میتونه دکمه‌هاش رو بزنه
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    # کلید اصلی پنل برای این چت
    key = f"panel_owner_{chat_id}"
    
    # ===== اگر پنلی برای این چت ثبت نشده =====
    if key not in context.chat_data:
        await query.answer("❌ هیچ پنل فعالی در این گروه وجود ندارد!", show_alert=True)
        return False
    
    # ===== مالک پنل رو بگیر =====
    owner_id = context.chat_data[key]
    
    # ===== اگر کاربر فعلی مالک نیست =====
    if owner_id != user_id:
        await query.answer("❌ این پنل متعلق به شما نیست!", show_alert=True)
        return False
    
    return True

async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            # پنل توسط کاربر دیگه‌ای باز شده
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

async def force_clear_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن اجباری پنل (برای ادمین یا شرایط خاص)"""
    chat_id = update.effective_chat.id
    key = f"panel_owner_{chat_id}"
    context.chat_data.pop(key, None)

