# handlers/panel_utils.py

from telegram import Update
from telegram.ext import ContextTypes

# ========================================
# توابع قفل پنل (جدا از بقیه برای جلوگیری از circular import)
# ========================================

async def check_ownership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    بررسی مالکیت پنل - هر کاربر فقط پنل خودش رو میتونه کنترل کنه
    برگردوندن False یعنی کاربر اجازه نداره و پیام خطا داده میشه
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    # کلید منحصر‌به‌فرد برای هر کاربر در هر چت
    key = f"panel_owner_{chat_id}_{user_id}"
    
    # چک میکنیم که آیا این کاربر پنل باز داره یا نه
    if key not in context.chat_data:
        await query.answer("❌ پنل شما بسته شده! لطفاً دوباره باز کن.", show_alert=True)
        return False
    
    return True

async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثبت مالکیت پنل برای کاربر - پنل قبلی رو پاک میکنه"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    # کلید منحصر‌به‌فرد برای هر کاربر
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

