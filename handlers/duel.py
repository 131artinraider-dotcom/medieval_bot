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
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        print(f"⚔️ دوئل شروع شد توسط کاربر {user_id} در گروه {chat_id}")
        
        # چک کردن پیام خصوصی
        if update.effective_chat.type == "private":
            await update.message.reply_text("❌ دوئل فقط در گروه‌ها قابل انجام است!")
            return
        
        # دریافت مبلغ
        text = update.message.text.strip()
        print(f"🔍 متن کامل: {text}")
        
        parts = text.split()
        print(f"🔍 parts: {parts}")
        
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ لطفاً مبلغ رو وارد کن!\n"
                "مثال: `/duel 500` یا `دوئل 500`",
                parse_mode="Markdown"
            )
            return
        
        try:
            amount = int(parts[1])
            print(f"🔍 مبلغ: {amount}")
        except ValueError as e:
            print(f"❌ خطا در تبدیل عدد: {e}")
            await update.message.reply_text("❌ مبلغ نامعتبر! لطفاً یک عدد وارد کن.")
            return
        
        if amount < 100:
            await update.message.reply_text("❌ حداقل مبلغ **۱۰۰ سکه** است!")
            return
        
        # بررسی سکه کاربر
        user_row = await get_user(user_id)
        print(f"🔍 user_row: {user_row}")
        
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
        
        # چک کردن دوئل فعال
        conn = await get_db()
        existing = await conn.fetchval(
            "SELECT id FROM active_duels WHERE chat_id = $1 AND accepted = FALSE",
            chat_id
        )
        
        if existing:
            await conn.close()
            await update.message.reply_text("⚠️ در حال حاضر یک دوئل فعال در این گروه وجود دارد!")
            return
        
        # کم کردن پول از سازنده
        await conn.execute(
            "UPDATE users SET gold = gold - $1 WHERE user_id = $2",
            amount, user_id
        )
        await conn.close()
        
        # ساخت دکمه‌ها
        keyboard = [
            [InlineKeyboardButton("⚔️ قبول دوئل", callback_data="duel_accept", style="success")],
            [InlineKeyboardButton("🔒 بستن دوئل", callback_data="duel_close", style="danger")]
        ]
        
        msg = (
            f"⚔️ **دوئل!**\n\n"
            f"🗡️ **{user_row['character_name']}** مبلغ **{amount:,}** سکه رو روی میز گذاشت!\n"
            f"💰 جایزه: {amount:,} سکه\n"
            f"⏱️ ۳۰ ثانیه فرصت داری!"
        )
        
        print("📤 ارسال پیام دوئل...")
        sent_msg = await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        print(f"✅ پیام دوئل ارسال شد! message_id: {sent_msg.message_id}")
        
        # ذخیره در دیتابیس
        conn = await get_db()
        await conn.execute("""
            INSERT INTO active_duels (chat_id, creator_id, creator_name, amount, message_id)
            VALUES ($1, $2, $3, $4, $5)
        """, chat_id, user_id, user_row['character_name'], amount, sent_msg.message_id)
        await conn.close()
        print("✅ دوئل در دیتابیس ذخیره شد!")
        
        # تایمر ۳۰ ثانیه
        await asyncio.sleep(30)
        
        # بررسی بعد از تایمر
        conn = await get_db()
        duel_data = await conn.fetchrow(
            "SELECT * FROM active_duels WHERE chat_id = $1 AND accepted = FALSE",
            chat_id
        )
        
        if duel_data:
            await conn.execute(
                "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
                amount, user_id
            )
            await conn.execute(
                "DELETE FROM active_duels WHERE chat_id = $1",
                chat_id
            )
            await conn.close()
            
            await sent_msg.edit_text(
                f"⏰ **زمان دوئل به اتمام رسید!**\n\n"
                f"هیچ کس دوئل رو قبول نکرد.\n"
                f"💔 مبلغ {amount:,} سکه برگشت.",
                parse_mode="Markdown"
            )
            print("⏰ تایمر تمام شد و دوئل حذف گردید.")
        else:
            await conn.close()
            print("✅ دوئل قبلا تکمیل شده بود.")
            
    except Exception as e:
        print(f"❌ خطا در تابع duel: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text("❌ خطایی در شروع دوئل رخ داد! لطفاً دوباره تلاش کن.")

# ========================================
# قبول دوئل
# ========================================
async def duel_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قبول کردن دوئل"""
    try:
        query = update.callback_query
        await query.answer("✅ دوئل قبول شد!")
        
        user_id = query.from_user.id
        chat_id = update.effective_chat.id
        
        print(f"🔍 قبول دوئل توسط کاربر {user_id} در گروه {chat_id}")
        
        conn = await get_db()
        
        # دریافت دوئل فعال
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
        
        # دریافت اطلاعات برنده و بازنده
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
        print("✅ دوئل تکمیل شد!")
        
    except Exception as e:
        print(f"❌ خطا در duel_accept: {e}")
        import traceback
        traceback.print_exc()

# ========================================
# بستن دوئل
# ========================================
async def duel_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن دوئل توسط سازنده"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = update.effective_chat.id
        
        print(f"🔒 بستن دوئل توسط کاربر {user_id} در گروه {chat_id}")
        
        conn = await get_db()
        
        duel = await conn.fetchrow(
            "SELECT * FROM active_duels WHERE chat_id = $1 AND accepted = FALSE",
            chat_id
        )
        
        if not duel:
            await query.edit_message_text("❌ این دوئل منقضی شده است!")
            await conn.close()
            return
        
        if user_id != duel['creator_id']:
            await query.edit_message_text("❌ فقط سازنده می‌تونه ببنده!")
            await conn.close()
            return
        
        amount = duel['amount']
        creator_id = duel['creator_id']
        
        # برگردوندن پول به سازنده
        await conn.execute(
            "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
            amount, creator_id
        )
        
        await conn.execute(
            "DELETE FROM active_duels WHERE chat_id = $1",
            chat_id
        )
        await conn.close()
        
        await query.edit_message_text(
            f"🔒 **دوئل بسته شد!**\n\n"
            f"💰 مبلغ {amount:,} سکه برگشت.",
            parse_mode="Markdown"
        )
        print("✅ دوئل بسته شد!")
        
    except Exception as e:
        print(f"❌ خطا در duel_close: {e}")
        import traceback
        traceback.print_exc()

