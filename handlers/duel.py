import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user, get_db

# ========================================
# شروع دوئل (ساده و بدون باگ)
# ========================================
async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع دوئل با مبلغ مشخص"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ دوئل فقط در گروه‌ها!")
        return
    
    # دریافت مبلغ
    parts = update.message.text.split()
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
    
    # دکمه‌ها
    keyboard = [[InlineKeyboardButton("⚔️ قبول دوئل", callback_data="duel_accept", style="success")]]
    
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
        INSERT INTO active_duels (chat_id, creator_id, creator_name, amount, message_id)
        VALUES ($1, $2, $3, $4, $5)
    """, chat_id, user_id, user_row['character_name'], amount, sent.message_id)
    await conn.close()
    
    # ===== تایمر ۳۰ ثانیه =====
    await asyncio.sleep(30)
    
    # ===== بررسی و برگردوندن پول =====
    conn = await get_db()
    duel = await conn.fetchrow(
        "SELECT * FROM active_duels WHERE chat_id = $1 AND accepted = FALSE",
        chat_id
    )
    
    if duel:
        await conn.execute(
            "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
            amount, user_id
        )
        await conn.execute(
            "DELETE FROM active_duels WHERE chat_id = $1",
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
# قبول دوئل
# ========================================
async def duel_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قبول کردن دوئل"""
    print("✅ دکمه دوئل کلیک شد!")
    
    query = update.callback_query
    await query.answer("✅ دوئل قبول شد!")
    
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    conn = await get_db()
    
    # دریافت دوئل
    duel = await conn.fetchrow(
        "SELECT * FROM active_duels WHERE chat_id = $1 AND accepted = FALSE",
        chat_id
    )
    
    if not duel:
        await query.edit_message_text("❌ این دوئل منقضی شده است!")
        await conn.close()
        return
    
    if user_id == duel['creator_id']:
        await query.edit_message_text("❌ نمی‌تونی دوئل خودت رو قبول کنی!")
        await conn.close()
        return
    
    amount = duel['amount']
    
    # بررسی سکه کاربر قبول کننده
    user_row = await get_user(user_id)
    if not user_row or not user_row['is_registered']:
        await query.edit_message_text("❌ ثبت‌نام نکردی!")
        await conn.close()
        return
    
    if user_row['gold'] < amount:
        await query.edit_message_text(f"❌ سکه کافی نیست! نیاز: {amount:,}")
        await conn.close()
        return
    
    # کم کردن پول از قبول کننده
    await conn.execute(
        "UPDATE users SET gold = gold - $1 WHERE user_id = $2",
        amount, user_id
    )
    
    # تعیین برنده (۵۰/۵۰)
    winner_id = duel['creator_id'] if random.random() < 0.5 else user_id
    
    # اضافه کردن پول به برنده
    await conn.execute(
        "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
        amount * 2, winner_id
    )
    
    winner_row = await conn.fetchrow(
        "SELECT character_name, gold FROM users WHERE user_id = $1",
        winner_id
    )
    
    loser_id = user_id if winner_id == duel['creator_id'] else duel['creator_id']
    loser_row = await conn.fetchrow(
        "SELECT character_name, gold FROM users WHERE user_id = $1",
        loser_id
    )
    
    # حذف دوئل
    await conn.execute(
        "DELETE FROM active_duels WHERE chat_id = $1",
        chat_id
    )
    await conn.close()
    
    await query.edit_message_text(
        f"⚔️ **نتیجه دوئل!**\n\n"
        f"🎲 **{winner_row['character_name']}** دوئل رو برد!\n\n"
        f"🏆 **{winner_row['character_name']}:** +{amount:,} سکه ({winner_row['gold']:,} سکه)\n"
        f"💔 **{loser_row['character_name']}:** -{amount:,} سکه ({loser_row['gold']:,} سکه)",
        parse_mode="Markdown"
    )

