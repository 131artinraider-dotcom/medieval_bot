import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user, get_db, create_duel, get_active_duel, accept_duel, delete_duel

# ========================================
# شروع دوئل
# ========================================
async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع دوئل با مبلغ مشخص"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    print(f"⚔️ دوئل شروع شد توسط کاربر {user_id} در گروه {chat_id}")
    
    # چک کردن پیام خصوصی
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ دوئل فقط در گروه‌ها قابل انجام است!")
        return
    
    # دریافت مبلغ
    text = update.message.text.strip()
    
    # پشتیبانی از هر دو فرمت
    if text.startswith("/duel"):
        parts = text.split()
    elif text.startswith("دوئل"):
        parts = ["دوئل"] + text[4:].strip().split()
    else:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n`/duel 1000` یا `دوئل 1000`",
            parse_mode="Markdown"
        )
        return
    
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ لطفاً مبلغ رو وارد کن!\n"
            "مثال: `/duel 500` یا `دوئل 500`",
            parse_mode="Markdown"
        )
        return
    
    try:
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ مبلغ نامعتبر! لطفاً یک عدد وارد کن.")
        return
    
    if amount < 100:
        await update.message.reply_text("❌ حداقل مبلغ **۱۰۰ سکه** است!")
        return
    
    # دریافت اطلاعات کاربر
    user_row = await get_user(user_id)
    if not user_row or not user_row['is_registered']:
        await update.message.reply_text("❌ شما ثبت‌نام نکردید!")
        return
    
    if user_row['gold'] < amount:
        await update.message.reply_text(
            f"❌ سکه کافی نیست!\n"
            f"💰 سکه‌های تو: {user_row['gold']:,}\n"
            f"💰 مبلغ دوئل: {amount:,}"
        )
        return
    
    # چک کردن دوئل فعال در گروه (از دیتابیس)
    existing_duel = await get_active_duel(chat_id)
    if existing_duel:
        await update.message.reply_text("⚠️ در حال حاضر یک دوئل فعال در این گروه وجود دارد!")
        return
    
    # کم کردن پول از سازنده
    conn = await get_db()
    await conn.execute(
        "UPDATE users SET gold = gold - $1 WHERE user_id = $2",
        amount, user_id
    )
    await conn.close()
    
    # ساخت پیام
    msg = (
        f"⚔️ **دوئل!**\n\n"
        f"🗡️ **{user_row['character_name']}** مبلغ **{amount:,}** سکه رو روی میز گذاشت!\n\n"
        f"💰 جایزه: **{amount:,}** سکه\n\n"
        f"🎲 برای قبول کردن، دکمه زیر رو بزن!\n"
        f"⏱️ ۳۰ ثانیه فرصت داری!"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚔️ قبول دوئل", callback_data="duel_accept", style="success")],
        [InlineKeyboardButton("🔒 بستن دوئل", callback_data="duel_close", style="danger")]
    ]
    
    sent_msg = await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    # ذخیره دوئل در دیتابیس
    await create_duel(chat_id, user_id, user_row['character_name'], amount, sent_msg.message_id)
    
    # ===== تایمر ۳۰ ثانیه =====
    await asyncio.sleep(30)
    
    # چک کن که دوئل هنوز فعاله
    duel_data = await get_active_duel(chat_id)
    if duel_data and not duel_data['accepted']:
        # برگردوندن پول به سازنده
        conn = await get_db()
        await conn.execute(
            "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
            amount, user_id
        )
        await conn.close()
        
        # حذف دوئل
        await delete_duel(chat_id)
        
        # ویرایش پیام
        msg = (
            f"⏰ **زمان دوئل به اتمام رسید!**\n\n"
            f"هیچ کس دوئل **{user_row['character_name']}** رو قبول نکرد.\n\n"
            f"💔 مبلغ {amount:,} سکه به حساب {user_row['character_name']} برگشت."
        )
        
        await sent_msg.edit_text(msg, parse_mode="Markdown")

# ========================================
# قبول دوئل
# ========================================
async def duel_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قبول کردن دوئل توسط کاربر دیگر"""
    print("✅ دکمه دوئل کلیک شد!")
    
    query = update.callback_query
    await query.answer("✅ دوئل قبول شد!")
    
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    # دریافت دوئل از دیتابیس
    duel_data = await get_active_duel(chat_id)
    
    if not duel_data:
        await query.edit_message_text("❌ این دوئل منقضی شده است!")
        print("❌ دوئل پیدا نشد!")
        return
    
    if user_id == duel_data['creator_id']:
        await query.edit_message_text("❌ نمی‌تونی دوئل خودت رو قبول کنی!")
        return
    
    if duel_data['accepted']:
        await query.edit_message_text("❌ این دوئل قبلا قبول شده است!")
        return
    
    amount = duel_data['amount']
    
    # بررسی سکه کاربر قبول کننده
    user_row = await get_user(user_id)
    if not user_row or not user_row['is_registered']:
        await query.edit_message_text("❌ ثبت‌نام نکردی!")
        return
    
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
    winner_id = duel_data['creator_id'] if random.random() < 0.5 else user_id
    
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
    
    loser_id = user_id if winner_id == duel_data['creator_id'] else duel_data['creator_id']
    loser_row = await conn.fetchrow(
        "SELECT character_name, gold FROM users WHERE user_id = $1",
        loser_id
    )
    await conn.close()
    
    # آپدیت دوئل در دیتابیس
    await accept_duel(chat_id, winner_id)
    
    # حذف دوئل از دیتابیس (بعد از اتمام)
    await delete_duel(chat_id)
    
    # آپدیت کوئست
    from database import update_quest_progress
    await update_quest_progress(winner_id, "duel")
    await update_quest_progress(loser_id, "duel")
    
    await query.edit_message_text(
        f"⚔️ **نتیجه دوئل!**\n\n"
        f"🎲 **{winner_row['character_name']}** دوئل رو برد!\n\n"
        f"🏆 **{winner_row['character_name']}:** +{amount:,} سکه ({winner_row['gold']:,} سکه)\n"
        f"💔 **{loser_row['character_name']}:** -{amount:,} سکه ({loser_row['gold']:,} سکه)",
        parse_mode="Markdown"
    )

# ========================================
# بستن دوئل (فقط سازنده)
# ========================================
async def duel_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن دوئل توسط سازنده"""
    query = update.callback_query
    print("🔒 دکمه بستن دوئل کلیک شد!")
    
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    # دریافت دوئل از دیتابیس
    duel_data = await get_active_duel(chat_id)
    
    if not duel_data:
        await query.answer("❌ این دوئل منقضی شده است!", show_alert=True)
        return
    
    # فقط سازنده میتونه ببنده
    if user_id != duel_data['creator_id']:
        await query.answer("❌ فقط سازنده دوئل می‌تونه آنرا ببندد!", show_alert=True)
        return
    
    amount = duel_data['amount']
    creator_id = duel_data['creator_id']
    
    # برگردوندن پول به سازنده
    conn = await get_db()
    await conn.execute(
        "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
        amount, creator_id
    )
    await conn.close()
    
    # حذف دوئل
    await delete_duel(chat_id)
    
    await query.edit_message_text(
        f"🔒 **دوئل بسته شد!**\n\n"
        f"💰 مبلغ {amount:,} سکه به {duel_data['creator_name']} برگشت.",
        parse_mode="Markdown"
    )

