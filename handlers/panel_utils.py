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
    
    # کلید باید وجود داشته باشه
    if key not in context.chat_data:
        await query.answer("❌ شما پنل فعالی ندارید! لطفاً پنل رو دوباره باز کن.", show_alert=True)
        return False
    
    return True

async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ثبت مالکیت پنل برای کاربر
    همه پنل‌های قبلی در این چت رو پاک میکنه
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    # ===== پاک کردن همه پنل‌های این چت =====
    for existing_key in list(context.chat_data.keys()):
        if existing_key.startswith(f"panel_owner_{chat_id}_"):
            context.chat_data.pop(existing_key, None)
    
    # ===== ثبت پنل جدید =====
    key = f"panel_owner_{chat_id}_{user_id}"
    context.chat_data[key] = user_id

async def clear_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن مالکیت پنل کاربر"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}_{user_id}"
    context.chat_data.pop(key, None)

