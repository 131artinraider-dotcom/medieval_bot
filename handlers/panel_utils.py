# handlers/panel_utils.py

import uuid
from telegram import Update
from telegram.ext import ContextTypes
from database import get_db

# ========================================
# توابع قفل پنل با دیتابیس
# ========================================

async def generate_panel_id() -> str:
    """تولید یک panel_id تصادفی"""
    return str(uuid.uuid4())[:8]

async def create_panel(user_id: int, panel_type: str, chat_id: int) -> str:
    """
    ایجاد یک پنل جدید در دیتابیس
    برمیگردونه: panel_id
    """
    panel_id = await generate_panel_id()
    
    conn = await get_db()
    await conn.execute("""
        INSERT INTO panels (panel_id, user_id, chat_id, panel_type, created_at)
        VALUES ($1, $2, $3, $4, NOW())
    """, panel_id, user_id, chat_id, panel_type)
    await conn.close()
    
    return panel_id

async def get_panel_owner(panel_id: str) -> int:
    """دریافت owner_id یک پنل از دیتابیس"""
    conn = await get_db()
    owner_id = await conn.fetchval(
        "SELECT user_id FROM panels WHERE panel_id = $1",
        panel_id
    )
    await conn.close()
    return owner_id

async def delete_panel(panel_id: str):
    """حذف پنل از دیتابیس"""
    conn = await get_db()
    await conn.execute(
        "DELETE FROM panels WHERE panel_id = $1",
        panel_id
    )
    await conn.close()

async def clear_user_panels(user_id: int, chat_id: int):
    """پاک کردن همه پنل‌های یک کاربر در یک چت"""
    conn = await get_db()
    await conn.execute(
        "DELETE FROM panels WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id
    )
    await conn.close()

async def check_panel_ownership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    بررسی مالکیت پنل با استفاده از panel_id در callback_data
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # ===== دریافت panel_id از callback_data =====
    data = query.data
    parts = data.split(":")
    
    if len(parts) < 2:
        await query.answer("❌ داده نامعتبر!", show_alert=True)
        return False
    
    panel_id = parts[1]
    
    # ===== دریافت owner_id از دیتابیس =====
    owner_id = await get_panel_owner(panel_id)
    
    if not owner_id:
        await query.answer("❌ این پنل منقضی شده است! لطفاً دوباره باز کن.", show_alert=True)
        return False
    
    # ===== چک کردن مالکیت =====
    if owner_id != user_id:
        await query.answer("❌ این پنل متعلق به شما نیست!", show_alert=True)
        return False
    
    # ذخیره panel_id در context برای استفاده بعدی
    context.user_data['current_panel_id'] = panel_id
    return True

async def set_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE, panel_type: str) -> str:
    """
    ثبت پنل جدید و برگردوندن panel_id
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    # ===== پاک کردن پنل‌های قبلی این کاربر =====
    await clear_user_panels(user_id, chat_id)
    
    # ===== ایجاد پنل جدید =====
    panel_id = await create_panel(user_id, panel_type, chat_id)
    
    # ذخیره در context برای استفاده بعدی
    context.user_data['current_panel_id'] = panel_id
    
    return panel_id

async def clear_panel_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن پنل کاربر"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    panel_id = context.user_data.get('current_panel_id')
    if panel_id:
        await delete_panel(panel_id)
        context.user_data.pop('current_panel_id', None)
    
    # همچنین پاک کردن همه پنل‌های این کاربر
    await clear_user_panels(user_id, chat_id)

