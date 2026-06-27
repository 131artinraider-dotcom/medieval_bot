import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user, get_db, update_quest_progress, add_group_member

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ دوئل فقط در گروه‌ها!")
        return

    text = update.message.text.strip()
    parts = text.split()

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

    user_row = await get_user(user_id)
    if not user_row or not user_row['is_registered']:
        await update.message.reply_text("❌ ثبت‌نام نکردی!")
        return

    if user_row['gold'] < amount:
        await update.message.reply_text(f"❌ سکه کافی نیست! داری: {user_row['gold']:,}")
        return

    # ثبت کاربر در لیدربرد گروه
    await add_group_member(user_id, chat_id)

    conn = await get_db()
    await conn.execute("UPDATE users SET gold = gold - $1 WHERE user_id = $2", amount, user_id)

    keyboard = [
        [InlineKeyboardButton("⚔️ قبول دوئل", callback_data="duel_accept", style="success")],
        [InlineKeyboardButton("🔒 بستن دوئل", callback_data="duel_close", style="danger")]
    ]

    sent = await update.message.reply_text(
        f"⚔️ **دوئل!**\n\n"
        f"🗡️ **{user_row['character_name']}** مبلغ **{amount:,}** سکه رو روی میز گذاشت!\n"
        f"💰 جایزه: {amount * 2:,} سکه\n"
        f"⏱️ ۳۰ ثانیه فرصت داری!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    await conn.execute("""
        INSERT INTO duel_requests (chat_id, creator_id, creator_name, amount, message_id)
        VALUES ($1, $2, $3, $4, $5)
    """, chat_id, user_id, user_row['character_name'], amount, sent.message_id)
    await conn.close()

    asyncio.create_task(duel_timer(chat_id, user_id, amount, sent))


async def duel_timer(chat_id: int, user_id: int, amount: int, sent_msg):
    await asyncio.sleep(30)
    conn = await get_db()
    duel_data = await conn.fetchrow(
        "SELECT * FROM duel_requests WHERE chat_id = $1 AND accepted = FALSE", chat_id
    )
    if duel_data:
        await conn.execute("UPDATE users SET gold = gold + $1 WHERE user_id = $2", amount, user_id)
        await conn.execute("DELETE FROM duel_requests WHERE chat_id = $1", chat_id)
        await conn.close()
        try:
            await sent_msg.edit_text(
                f"⏰ **زمان دوئل به اتمام رسید!**\n\n💔 مبلغ {amount:,} سکه برگشت.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    else:
        await conn.close()


async def duel_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id

    conn = await get_db()
    duel = await conn.fetchrow(
        "SELECT * FROM duel_requests WHERE chat_id = $1 AND accepted = FALSE", chat_id
    )

    if not duel:
        await query.answer("❌ این دوئل منقضی شده است!", show_alert=True)
        await conn.close()
        return

    if user_id == duel['creator_id']:
        await query.answer("❌ نمی‌تونی دوئل خودت رو قبول کنی!", show_alert=True)
        await conn.close()
        return

    amount = duel['amount']
    user_row = await get_user(user_id)

    if not user_row or not user_row['is_registered']:
        await query.answer("❌ ثبت‌نام نکردی!", show_alert=True)
        await conn.close()
        return

    if user_row['gold'] < amount:
        await query.answer(f"❌ سکه کافی نیست! نیاز: {amount:,}", show_alert=True)
        await conn.close()
        return

    await query.answer("✅ دوئل قبول شد!")

    # ثبت هر دو در لیدربرد گروه
    await add_group_member(user_id, chat_id)
    await add_group_member(duel['creator_id'], chat_id)

    await conn.execute("UPDATE users SET gold = gold - $1 WHERE user_id = $2", amount, user_id)

    # تعیین برنده با در نظر گرفتن spd و lck
    creator_row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", duel['creator_id'])
    challenger_row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

    # شانس بر اساس spd + lck هر دو نفر
    creator_score = (creator_row['spd'] or 10) + (creator_row['lck'] or 10)
    challenger_score = (challenger_row['spd'] or 10) + (challenger_row['lck'] or 10)
    total = creator_score + challenger_score
    creator_win_chance = creator_score / total

    winner_id = duel['creator_id'] if random.random() < creator_win_chance else user_id
    loser_id = user_id if winner_id == duel['creator_id'] else duel['creator_id']

    await conn.execute("UPDATE users SET gold = gold + $1 WHERE user_id = $2", amount * 2, winner_id)
    await conn.execute("DELETE FROM duel_requests WHERE chat_id = $1", chat_id)

    winner_row = await conn.fetchrow("SELECT character_name, gold FROM users WHERE user_id = $1", winner_id)
    loser_row = await conn.fetchrow("SELECT character_name, gold FROM users WHERE user_id = $1", loser_id)
    await conn.close()

    # ✅ آپدیت کوئست دوئل برای هر دو نفر
    await update_quest_progress(winner_id, "duel", 1)
    await update_quest_progress(loser_id, "duel", 1)

    # نمایش شانس
    winner_chance = int(creator_win_chance * 100) if winner_id == duel['creator_id'] else int((1 - creator_win_chance) * 100)

    await query.edit_message_text(
        f"⚔️ **نتیجه دوئل!**\n\n"
        f"🎲 **{winner_row['character_name']}** دوئل رو برد! (شانس {winner_chance}٪)\n\n"
        f"🏆 **{winner_row['character_name']}:** +{amount:,} سکه ({winner_row['gold']:,} سکه)\n"
        f"💔 **{loser_row['character_name']}:** -{amount:,} سکه ({loser_row['gold']:,} سکه)",
        parse_mode="Markdown"
    )


async def duel_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = update.effective_chat.id

    conn = await get_db()
    duel = await conn.fetchrow(
        "SELECT * FROM duel_requests WHERE chat_id = $1 AND accepted = FALSE", chat_id
    )

    if not duel:
        await query.answer("❌ این دوئل منقضی شده است!", show_alert=True)
        await conn.close()
        return

    if user_id != duel['creator_id']:
        await query.answer("❌ فقط سازنده می‌تونه ببنده!", show_alert=True)
        await conn.close()
        return

    amount = duel['amount']
    await conn.execute("UPDATE users SET gold = gold + $1 WHERE user_id = $2", amount, duel['creator_id'])
    await conn.execute("DELETE FROM duel_requests WHERE chat_id = $1", chat_id)
    await conn.close()

    await query.edit_message_text(
        f"🔒 **دوئل بسته شد!**\n\n💰 مبلغ {amount:,} سکه برگشت.",
        parse_mode="Markdown"
    )
