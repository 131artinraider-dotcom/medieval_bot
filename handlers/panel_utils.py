# handlers/panel_utils.py

from telegram import Update
from telegram.ext import ContextTypes

# ========================================
# توابع قفل پنل - نسخه نهایی
# ========================================

async def ensure_panel_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
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
    
    # ===== مالک خودشه =====
    return True

async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    ثبت مالکیت پنل برای کاربر
    اگر پنل دیگه‌ای باز باشه، اجازه نمیده
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
        # اگر مال خودشه، اجازه بده
        return True
    
    # ===== ثبت پنل جدید =====
    context.chat_data[key] = user_id
    return True

async def clear_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن مالکیت پنل - فقط مالک میتونه پاک کنه"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    key = f"panel_owner_{chat_id}"
    
    # ===== فقط اگه پنل وجود داشته باشه و مالک باشه =====
    if key in context.chat_data and context.chat_data[key] == user_id:
        context.chat_data.pop(key, None)
        print(f"🧹 پنل چت {chat_id} توسط کاربر {user_id} بسته شد")
    else:
        print(f"⚠️ کاربر {user_id} تلاش کرد پنلی که مالکش نیست رو ببنده")

# ===== alias برای سازگاری با کدهای قدیمی =====
check_ownership = ensure_panel_access

