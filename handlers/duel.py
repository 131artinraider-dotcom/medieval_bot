import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user, get_db

# ========================================
# شروع دوئل
# ========================================
async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع دوئل با مبلغ مشخص"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    print(f"⚔️ دوئل شروع شد توسط کاربر {user_id} در گروه {chat_id}")
    
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ دوئل فقط در گروه‌ها!")
        return
    
    # دریافت مبلغ
    text = update.message.text.strip()
    if text.startswith("/duel") or text.startswith("دوئل"):
        parts = text.split()
    else:
        await update.message.reply_text("❌ فرمت صحیح: /duel 1000")
        return
    
    if len(parts) < 2:
        await update.message.reply_text("❌ مبلغ رو وارد کن! مثال: /duel 500")
        return
    
    try:
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کن!")
        return
    
    if amount < 100:
        await update.message.reply_text("❌ حداقل ۱۰۰ سکه!")
        return
    
    # بررسی سکه کاربر
    user_row = await get_user(user_id)
    if not user_row or not user_row['is_registered']:
        await update.message.reply_text("❌ ثبت‌نام نکردی!")
        return
    
    if user_row['gold'] < amount:
        await update.message.reply_text(f"❌ سکه کافی نیست! داری: {user_row['gold']}")
        return
    
    # کم کردن پول از سازنده
    conn = await get_db()
    await conn.execute(
        "UPDATE users SET gold = gold - $1 WHERE user_id = $2",
        amount, user_id
    )
    await conn.close()
    
    # ===== دکمه‌ها با دکمه تست =====
    keyboard = [
        [InlineKeyboardButton("⚔️ قبول دوئل", callback_data="duel_accept", style="success")],
        [InlineKeyboardButton("🔒 بستن دوئل", callback_data="duel_close", style="danger")],
        [InlineKeyboardButton("🧪 دکمه تست", callback_data="test_button", style="primary")]
    ]
    
    sent = await update.message.reply_text(
        f"⚔️ **دوئل!**\n\n"
        f"🗡️ **{user_row['character_name']}** مبلغ **{amount:,}** سکه رو روی میز گذاشت!\n"
        f"💰 جایزه: {amount:,} سکه\n"
        f"⏱️ ۳۰ ثانیه فرصت داری!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    # ===== ذخیره در دیتابیس =====
    conn = await get_db()
    await conn.execute("""
        INSERT INTO duel_requests (chat_id, creator_id, creator_name, amount, message_id)
        VALUES ($1, $2, $3, $4, $5)
    """, chat_id, user_id, user_row['character_name'], amount, sent.message_id)
    await conn.close()
    
    print(f"📝 دوئل در دیتابیس ذخیره شد! chat_id: {chat_id}")
    
    # ===== تایمر ۳۰ ثانیه =====
    await asyncio.sleep(30)
    
    # ===== بررسی بعد از تایمر =====
    conn = await get_db()
    duel_data = await conn.fetchrow(
        "SELECT * FROM duel_requests WHERE chat_id = $1 AND accepted = FALSE",
        chat_id
    )
    
    if duel_data:
        await conn.execute(
            "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
            amount, user_id
        )
        await conn.execute(
            "DELETE FROM duel_requests WHERE chat_id = $1",
            chat_id
        )
        await conn.close()
        
        await sent.edit_text(
            f"⏰ **زمان دوئل به اتمام رسید!**\n\n"
            f"💔 مبلغ {amount:,} سکه برگشت.",
            parse_mode="Markdown"
        )
    else:
        await conn.close()

# ========================================
# قبول دوئل (ساده برای تست)
# ========================================
async def duel_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قبول کردن دوئل - نسخه تست"""
    print("🔥 تابع duel_accept اجرا شد!")
    
    query = update.callback_query
    await query.answer("✅ در حال پردازش...")
    
    # ===== پیام تست ساده =====
    await query.edit_message_text("✅ دکمه قبول دوئل کار کرد! (تست)")
    print("🔥 پیام تست ارسال شد!")

# ========================================
# بستن دوئل (ساده برای تست)
# ========================================
async def duel_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن دوئل - نسخه تست"""
    print("🔒 تابع duel_close اجرا شد!")
    
    query = update.callback_query
    await query.answer("✅ بسته شد!")
    await query.edit_message_text("🔒 دوئل بسته شد! (تست)")
    print("🔒 پیام تست ارسال شد!")

