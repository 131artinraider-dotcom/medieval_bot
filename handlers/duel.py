import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user, get_db

# ========================================
# دیکشنری دوئل‌های فعال
# ========================================
active_duels = {}

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
    
    duel_key = f"duel_{chat_id}"
    if duel_key in active_duels:
        await update.message.reply_text("⚠️ یک دوئل فعال هست!")
        return
    
    # کم کردن پول از سازنده
    conn = await get_db()
    await conn.execute(
        "UPDATE users SET gold = gold - $1 WHERE user_id = $2",
        amount, user_id
    )
    await conn.close()
    
    active_duels[duel_key] = {
        "creator_id": user_id,
        "creator_name": user_row['character_name'],
        "amount": amount,
        "accepted": False,
        "message_id": None
    }
    
    keyboard = [[InlineKeyboardButton("⚔️ قبول دوئل", callback_data="duel_accept", style="success")]]
    
    sent = await update.message.reply_text(
        f"⚔️ **دوئل!**\n\n"
        f"🗡️ **{user_row['character_name']}** مبلغ **{amount:,}** سکه رو روی میز گذاشت!\n"
        f"💰 جایزه: {amount:,} سکه\n"
        f"⏱️ ۳۰ ثانیه فرصت داری!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    active_duels[duel_key]["message_id"] = sent.message_id
    
    print(f"📝 دوئل ذخیره شد: {duel_key}")
    
    # ===== تایمر ۳۰ ثانیه =====
    await asyncio.sleep(30)
    
    if duel_key in active_duels and not active_duels[duel_key]["accepted"]:
        conn = await get_db()
        await conn.execute(
            "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
            amount, user_id
        )
        await conn.close()
        
        del active_duels[duel_key]
        
        await sent.edit_text(
            f"⏰ **زمان دوئل به اتمام رسید!**\n\n"
            f"💔 مبلغ {amount:,} سکه برگشت.",
            parse_mode="Markdown"
        )

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
    duel_key = f"duel_{chat_id}"
    
    print(f"🔍 duel_key: {duel_key}")
    print(f"🔍 active_duels: {active_duels}")
    
    if duel_key not in active_duels:
        await query.edit_message_text("❌ این دوئل منقضی شده است!")
        print("❌ دوئل پیدا نشد!")
        return
    
    duel_data = active_duels[duel_key]
    
    if user_id == duel_data["creator_id"]:
        await query.edit_message_text("❌ نمی‌تونی دوئل خودت رو قبول کنی!")
        return
    
    if duel_data["accepted"]:
        await query.edit_message_text("❌ این دوئل قبلا قبول شده است!")
        return
    
    # بررسی سکه کاربر قبول کننده
    user_row = await get_user(user_id)
    if not user_row or not user_row['is_registered']:
        await query.edit_message_text("❌ ثبت‌نام نکردی!")
        return
    
    amount = duel_data["amount"]
    
    if user_row['gold'] < amount:
        await query.edit_message_text(f"❌ سکه کافی نیست! نیاز: {amount:,}")
        return
    
    # کم کردن پول از قبول کننده
    conn = await get_db()
    await conn.execute(
        "UPDATE users SET gold = gold - $1 WHERE user_id = $2",
        amount, user_id
    )
    await conn.close()
    
    # تعیین برنده (۵۰/۵۰)
    winner_id = duel_data["creator_id"] if random.random() < 0.5 else user_id
    
    # اضافه کردن پول به برنده
    conn = await get_db()
    await conn.execute(
        "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
        amount * 2, winner_id
    )
    
    winner_row = await conn.fetchrow(
        "SELECT character_name, gold FROM users WHERE user_id = $1",
        winner_id
    )
    
    loser_id = user_id if winner_id == duel_data["creator_id"] else duel_data["creator_id"]
    loser_row = await conn.fetchrow(
        "SELECT character_name, gold FROM users WHERE user_id = $1",
        loser_id
    )
    await conn.close()
    
    duel_data["accepted"] = True
    del active_duels[duel_key]
    
    await query.edit_message_text(
        f"⚔️ **نتیجه دوئل!**\n\n"
        f"🎲 **{winner_row['character_name']}** دوئل رو برد!\n\n"
        f"🏆 **{winner_row['character_name']}:** +{amount:,} سکه ({winner_row['gold']:,} سکه)\n"
        f"💔 **{loser_row['character_name']}:** -{amount:,} سکه ({loser_row['gold']:,} سکه)",
        parse_mode="Markdown"
    )

