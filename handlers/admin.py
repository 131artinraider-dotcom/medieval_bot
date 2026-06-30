from telegram import Update
from telegram.ext import ContextTypes
from database import get_db
from config import ADMIN_ID

# ===== چک کردن ادمین =====
async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ===== پنل ادمین =====
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پنل ادمین"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    msg = (
        "👑 **پنل ادمین**\n\n"
        "**راهنمای استفاده:**\n\n"
        "💰 **مدیریت سکه:**\n"
        "   `/addgold 1000` (ریپلای)\n"
        "   `/removegold 500` (ریپلای)\n\n"
        "📈 **مدیریت اکس‌پی:**\n"
        "   `/addexp 100` (ریپلای)\n"
        "   `/removeexp 50` (ریپلای)\n\n"
        "⭐ **مدیریت آپگرید پوینت:**\n"
        "   `/addupgrade 5` (ریپلای)\n"
        "   `/removeupgrade 3` (ریپلای)\n\n"
        "📋 **مدیریت کوئست‌ها:**\n"
        "   `/resetquests` (ریپلای به کاربر) → ریست کوئست‌های یه کاربر\n"
        "   `/resetallquests` → ریست همه کوئست‌ها\n\n"
        "🗑️ **ریست کامل کاربر:**\n"
        "   `/reset` (ریپلای)\n\n"
        "📜 **لاگ پیام‌های گروه:**\n"
        "   `/logs` → مرور پیام‌های همین گروه\n"
        "   `/logs کلمه` → فیلتر پیام‌های شامل کلمه\n"
        "   `/chats` (در پیوی) → لیست گروه‌های لاگ‌شده\n"
        "   `/logs <chat_id> [کلمه]` (در پیوی)\n\n"
        "⚠️ برای همه کامندها، **به پیام کاربر ریپلای کن**!"
    )
    
    await update.message.reply_text(
        msg,
        parse_mode="Markdown"
    )

# ===== اضافه کردن پول =====
async def admin_add_gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اضافه کردن پول به کاربر (با ریپلای)"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لطفاً به پیام کاربر مورد نظر **ریپلای** کن!\n"
            "مثال: /addgold 1000 (ریپلای به پیام کاربر)"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ لطفاً مقدار رو وارد کن! مثال: /addgold 1000")
            return
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ مقدار نامعتبر! لطفاً یک عدد وارد کن.")
        return
    
    conn = await get_db()
    
    user_exists = await conn.fetchval(
        "SELECT user_id FROM users WHERE user_id = $1",
        target_user.id
    )
    
    if not user_exists:
        await conn.close()
        await update.message.reply_text(
            f"❌ کاربر **{target_user.first_name}** در دیتابیس وجود ندارد!"
        )
        return
    
    await conn.execute(
        "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
        amount, target_user.id
    )
    
    new_gold = await conn.fetchval(
        "SELECT gold FROM users WHERE user_id = $1",
        target_user.id
    )
    
    await conn.close()
    
    await update.message.reply_text(
        f"✅ **{amount:,} سکه** به **{target_user.first_name}** اضافه شد!\n"
        f"💰 سکه جدید: {new_gold:,}",
        parse_mode="Markdown"
    )

# ===== کم کردن پول =====
async def admin_remove_gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کم کردن پول از کاربر (با ریپلای)"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لطفاً به پیام کاربر مورد نظر **ریپلای** کن!\n"
            "مثال: /removegold 500 (ریپلای به پیام کاربر)"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ لطفاً مقدار رو وارد کن! مثال: /removegold 500")
            return
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ مقدار نامعتبر! لطفاً یک عدد وارد کن.")
        return
    
    conn = await get_db()
    
    user_exists = await conn.fetchval(
        "SELECT user_id FROM users WHERE user_id = $1",
        target_user.id
    )
    
    if not user_exists:
        await conn.close()
        await update.message.reply_text(
            f"❌ کاربر **{target_user.first_name}** در دیتابیس وجود ندارد!"
        )
        return
    
    current_gold = await conn.fetchval(
        "SELECT gold FROM users WHERE user_id = $1",
        target_user.id
    )
    
    if current_gold < amount:
        await conn.close()
        await update.message.reply_text(
            f"❌ کاربر فقط {current_gold:,} سکه داره!\n"
            f"نمی‌تونی بیشتر از این کم کنی."
        )
        return
    
    await conn.execute(
        "UPDATE users SET gold = gold - $1 WHERE user_id = $2",
        amount, target_user.id
    )
    
    new_gold = await conn.fetchval(
        "SELECT gold FROM users WHERE user_id = $1",
        target_user.id
    )
    
    await conn.close()
    
    await update.message.reply_text(
        f"✅ **{amount:,} سکه** از **{target_user.first_name}** کم شد!\n"
        f"💰 سکه جدید: {new_gold:,}",
        parse_mode="Markdown"
    )

# ===== ریست کامل کاربر =====
async def admin_reset_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ریست کامل کاربر (با ریپلای)"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لطفاً به پیام کاربر مورد نظر **ریپلای** کن!\n"
            "مثال: /reset (ریپلای به پیام کاربر)"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    conn = await get_db()
    
    user_exists = await conn.fetchval(
        "SELECT user_id FROM users WHERE user_id = $1",
        target_user.id
    )
    
    if not user_exists:
        await conn.close()
        await update.message.reply_text(
            f"❌ کاربر **{target_user.first_name}** در دیتابیس وجود ندارد!"
        )
        return
    
    # حذف از inventory
    await conn.execute("DELETE FROM inventory WHERE user_id = $1", target_user.id)
    
    # حذف از dungeons
    await conn.execute("DELETE FROM dungeons WHERE user_id = $1", target_user.id)
    
    # حذف از daily_quests
    await conn.execute("DELETE FROM daily_quests WHERE user_id = $1", target_user.id)
    
    # حذف از users
    await conn.execute("DELETE FROM users WHERE user_id = $1", target_user.id)
    
    await conn.close()
    
    await update.message.reply_text(
        f"✅ **کاربر {target_user.first_name} با موفقیت ریست شد!**\n\n"
        f"کاربر از بیخ حذف شد و باید دوباره ثبت‌نام کنه.",
        parse_mode="Markdown"
    )

# ===== اضافه کردن اکس‌پی =====
async def admin_add_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اضافه کردن اکس‌پی به کاربر با لول آپ (با ریپلای)"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لطفاً به پیام کاربر مورد نظر **ریپلای** کن!\n"
            "مثال: /addexp 100 (ریپلای به پیام کاربر)"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ لطفاً مقدار رو وارد کن! مثال: /addexp 100")
            return
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ مقدار نامعتبر! لطفاً یک عدد وارد کن.")
        return
    
    from database import add_exp
    
    # ===== استفاده از تابع add_exp =====
    result = await add_exp(target_user.id, amount)
    
    if not result:
        await update.message.reply_text(
            f"❌ کاربر **{target_user.first_name}** در دیتابیس وجود ندارد!"
        )
        return
    
    msg = (
        f"✅ **{amount} اکس‌پی** به **{target_user.first_name}** اضافه شد!\n"
        f"📈 اکس‌پی جدید: {result['new_exp']} / {result['new_max_exp']}\n"
        f"⭐ لول جدید: {result['new_level']}"
    )
    
    if result['leveled_up']:
        msg += f"\n🎉 **لول آپ!** به لول {result['new_level']} رسیدی!"
    
    await update.message.reply_text(
        msg,
        parse_mode="Markdown"
    )

# ===== حذف اکس‌پی =====
async def admin_remove_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف اکس‌پی از کاربر (با ریپلای)"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لطفاً به پیام کاربر مورد نظر **ریپلای** کن!\n"
            "مثال: /removeexp 50 (ریپلای به پیام کاربر)"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ لطفاً مقدار رو وارد کن! مثال: /removeexp 50")
            return
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ مقدار نامعتبر! لطفاً یک عدد وارد کن.")
        return
    
    conn = await get_db()
    
    current_exp = await conn.fetchval(
        "SELECT exp FROM users WHERE user_id = $1",
        target_user.id
    )
    
    if current_exp < amount:
        await conn.close()
        await update.message.reply_text(
            f"❌ کاربر فقط {current_exp} اکس‌پی داره!\n"
            f"نمی‌تونی بیشتر از این کم کنی."
        )
        return
    
    await conn.execute(
        "UPDATE users SET exp = exp - $1 WHERE user_id = $2",
        amount, target_user.id
    )
    
    new_exp = await conn.fetchval(
        "SELECT exp FROM users WHERE user_id = $1",
        target_user.id
    )
    
    await conn.close()
    
    await update.message.reply_text(
        f"✅ **{amount} اکس‌پی** از **{target_user.first_name}** کم شد!\n"
        f"📈 اکس‌پی جدید: {new_exp}",
        parse_mode="Markdown"
    )

# ===== اضافه کردن آپگرید پوینت =====
async def admin_add_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اضافه کردن آپگرید پوینت به کاربر (با ریپلای)"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لطفاً به پیام کاربر مورد نظر **ریپلای** کن!\n"
            "مثال: /addupgrade 5 (ریپلای به پیام کاربر)"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ لطفاً مقدار رو وارد کن! مثال: /addupgrade 5")
            return
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ مقدار نامعتبر! لطفاً یک عدد وارد کن.")
        return
    
    conn = await get_db()
    
    user_exists = await conn.fetchval(
        "SELECT user_id FROM users WHERE user_id = $1",
        target_user.id
    )
    
    if not user_exists:
        await conn.close()
        await update.message.reply_text(
            f"❌ کاربر **{target_user.first_name}** در دیتابیس وجود ندارد!"
        )
        return
    
    await conn.execute(
        "UPDATE users SET upgrade_points = upgrade_points + $1 WHERE user_id = $2",
        amount, target_user.id
    )
    
    new_upgrade = await conn.fetchval(
        "SELECT upgrade_points FROM users WHERE user_id = $1",
        target_user.id
    )
    
    await conn.close()
    
    await update.message.reply_text(
        f"✅ **{amount} آپگرید پوینت** به **{target_user.first_name}** اضافه شد!\n"
        f"⭐ آپگرید پوینت جدید: {new_upgrade}",
        parse_mode="Markdown"
    )

# ===== حذف آپگرید پوینت =====
async def admin_remove_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف آپگرید پوینت از کاربر (با ریپلای)"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لطفاً به پیام کاربر مورد نظر **ریپلای** کن!\n"
            "مثال: /removeupgrade 3 (ریپلای به پیام کاربر)"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ لطفاً مقدار رو وارد کن! مثال: /removeupgrade 3")
            return
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ مقدار نامعتبر! لطفاً یک عدد وارد کن.")
        return
    
    conn = await get_db()
    
    user_exists = await conn.fetchval(
        "SELECT user_id FROM users WHERE user_id = $1",
        target_user.id
    )
    
    if not user_exists:
        await conn.close()
        await update.message.reply_text(
            f"❌ کاربر **{target_user.first_name}** در دیتابیس وجود ندارد!"
        )
        return
    
    current_upgrade = await conn.fetchval(
        "SELECT upgrade_points FROM users WHERE user_id = $1",
        target_user.id
    )
    
    if current_upgrade < amount:
        await conn.close()
        await update.message.reply_text(
            f"❌ کاربر فقط {current_upgrade} آپگرید پوینت داره!\n"
            f"نمی‌تونی بیشتر از این کم کنی."
        )
        return
    
    await conn.execute(
        "UPDATE users SET upgrade_points = upgrade_points - $1 WHERE user_id = $2",
        amount, target_user.id
    )
    
    new_upgrade = await conn.fetchval(
        "SELECT upgrade_points FROM users WHERE user_id = $1",
        target_user.id
    )
    
    await conn.close()
    
    await update.message.reply_text(
        f"✅ **{amount} آپگرید پوینت** از **{target_user.first_name}** کم شد!\n"
        f"⭐ آپگرید پوینت جدید: {new_upgrade}",
        parse_mode="Markdown"
    )

# ===== ریست کوئست‌های کاربر =====
async def admin_reset_quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ریست کوئست‌های کاربر (فقط ادمین)"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لطفاً به پیام کاربر مورد نظر **ریپلای** کن!\n"
            "مثال: /resetquests (ریپلای به پیام کاربر)"
        )
        return
    
    target_user = update.message.reply_to_message.from_user
    
    conn = await get_db()
    
    # حذف کوئست‌های کاربر
    await conn.execute(
        "DELETE FROM daily_quests WHERE user_id = $1",
        target_user.id
    )
    await conn.close()
    
    await update.message.reply_text(
        f"✅ کوئست‌های **{target_user.first_name}** ریست شد!\n"
        f"📋 کوئست‌های جدید برایش تولید میشن.",
        parse_mode="Markdown"
    )

# ===== ریست کوئست‌های همه کاربران =====
async def admin_reset_all_quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ریست کوئست‌های همه کاربران (فقط ادمین)"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    conn = await get_db()
    await conn.execute("DELETE FROM daily_quests")
    await conn.close()
    
    await update.message.reply_text(
        "✅ **همه کوئست‌ها ریست شدند!**\n"
        "📋 همه کاربران کوئست‌های جدید دریافت میکنن.",
        parse_mode="Markdown"
    )


# ===== تغییر اسم پلیر =====
async def admin_rename_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر اسم پلیر (فقط ادمین) - ریپلای + اسم جدید"""
    user_id = update.effective_user.id

    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ به پیام کاربر ریپلای کن!\n"
            "مثال: /rename اسم_جدید (ریپلای)"
        )
        return

    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("❌ اسم جدید رو وارد کن! مثال: /rename شوالیه_آهنین")
        return

    new_name = parts[1].strip()
    if len(new_name) < 2 or len(new_name) > 20:
        await update.message.reply_text("❌ اسم باید ۲ تا ۲۰ کاراکتر باشه!")
        return

    target_user = update.message.reply_to_message.from_user
    conn = await get_db()

    # چک وجود کاربر
    exists = await conn.fetchval("SELECT user_id FROM users WHERE user_id = $1", target_user.id)
    if not exists:
        await conn.close()
        await update.message.reply_text(f"❌ کاربر {target_user.first_name} در دیتابیس نیست!")
        return

    # چک تکراری بودن اسم
    name_taken = await conn.fetchval(
        "SELECT user_id FROM users WHERE character_name = $1 AND user_id != $2",
        new_name, target_user.id
    )
    if name_taken:
        await conn.close()
        await update.message.reply_text(f"❌ اسم «{new_name}» قبلاً گرفته شده!")
        return

    old_name = await conn.fetchval("SELECT character_name FROM users WHERE user_id = $1", target_user.id)
    await conn.execute("UPDATE users SET character_name = $1 WHERE user_id = $2", new_name, target_user.id)
    await conn.close()

    await update.message.reply_text(
        f"✅ اسم پلیر تغییر کرد!\n\n"
        f"👤 قبلی: **{old_name}**\n"
        f"✏️ جدید: **{new_name}**",
        parse_mode="Markdown"
    )


# ===== بستن همه پنل‌های باز =====
async def admin_close_all_panels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن همه پنل‌های باز همه کاربران (فقط ادمین)"""
    user_id = update.effective_user.id

    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return

    # پیدا کردن همه پنل‌های ثبت‌شده در bot_data
    panel_keys = [k for k in context.bot_data.keys() if k.startswith("panel_")]
    closed = 0
    failed = 0

    for key in panel_keys:
        data = context.bot_data.get(key)
        if not data:
            continue
        try:
            chat_id = data.get("chat_id")
            message_id = int(key.replace("panel_", ""))
            if chat_id:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                closed += 1
        except Exception:
            failed += 1
        finally:
            context.bot_data.pop(key, None)

    await update.message.reply_text(
        f"✅ **بستن پنل‌ها تموم شد!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗑️ بسته شد: {closed}\n"
        f"⚠️ خطا: {failed}\n"
        f"📋 باقی‌مونده: {len([k for k in context.bot_data.keys() if k.startswith('panel_')])}",
        parse_mode="Markdown"
    )


# ===== ریست دانجن کاربر =====
async def admin_reset_dungeon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ریست دانجن گیر کرده کاربر (فقط ادمین)"""
    user_id = update.effective_user.id

    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ به پیام کاربر ریپلای کن!\n"
            "مثال: /resetdungeon (ریپلای)"
        )
        return

    target_user = update.message.reply_to_message.from_user

    conn = await get_db()
    dungeon = await conn.fetchrow(
        "SELECT * FROM dungeons WHERE user_id = $1", target_user.id
    )

    if not dungeon:
        await conn.close()
        await update.message.reply_text(
            f"⚠️ **{target_user.first_name}** هیچ دانجن فعالی در دیتابیس نداره!"
        )
        return

    await conn.execute("DELETE FROM dungeons WHERE user_id = $1", target_user.id)
    await conn.close()

    await update.message.reply_text(
        f"✅ دانجن **{target_user.first_name}** ریست شد!\n"
        f"الان میتونه دوباره دانجن بزنه.",
        parse_mode="Markdown"
    )
