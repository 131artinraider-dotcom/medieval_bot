# handlers/panel_utils.py

from telegram import Update
from telegram.ext import ContextTypes

# ========================================
# توابع قفل پنل
# ========================================

async def check_ownership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    بررسی مالکیت پنل - فقط مالک پنل میتونه دکمه‌هاش رو بزنه
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}_{user_id}"
    
    # ===== اگر کلید وجود نداشته باشه =====
    if key not in context.chat_data:
        # ===== ببینیم آیا پنل دیگه‌ای باز هست؟ =====
        for existing_key in list(context.chat_data.keys()):
            if existing_key.startswith(f"panel_owner_{chat_id}_"):
                # پنل دیگه‌ای باز هست
                await query.answer("❌ یک پنل دیگر در این گروه باز است! لطفاً صبر کنید.", show_alert=True)
                return False
        
        # ===== هیچ پنلی باز نیست، پس این کاربر میتونه پنل جدید باز کنه =====
        context.chat_data[key] = user_id
        return True
    
    return True

async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ثبت مالکیت پنل برای کاربر
    فقط پنل قبلی خود کاربر رو پاک میکنه
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}_{user_id}"
    
    # ===== فقط پنل قبلی خود این کاربر رو پاک کن =====
    context.chat_data.pop(key, None)
    
    # ===== ثبت پنل جدید =====
    context.chat_data[key] = user_id

async def clear_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن مالکیت پنل کاربر"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}_{user_id}"
    context.chat_data.pop(key, None)

