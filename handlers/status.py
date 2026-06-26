from telegram import Update
from telegram.ext import ContextTypes
from database import get_user, get_db, get_respawn_time, check_respawn, update_quest_progress
from models import Player


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت کامل کاربر"""
    user_id = update.effective_user.id
    
    # ===== چک کردن ری‌اسپان =====
    await check_respawn(user_id)
    
    row = await get_user(user_id)
    player = Player.from_db_row(row)
    
    if not player or not player.is_registered:
        await update.message.reply_text(
            "❌ شما هنوز شخصیت خودت رو نساختی!\n"
            "برای شروع از /start یا 'شروع' استفاده کن."
        )
        return
    
    # دریافت آپگرید پوینت از دیتابیس
    conn = await get_db()
    upgrade_points = await conn.fetchval(
        "SELECT upgrade_points FROM users WHERE user_id = $1",
        user_id
    )
    
    # دریافت سکه فعلی برای کوئست
    current_gold = player.stats.gold
    await conn.close()
    
    # ===== آپدیت کوئست جمع‌آوری سکه =====
    await update_quest_progress(user_id, "gold", current_gold)
    
    # ===== ساخت پیام وضعیت =====
    status_text = (
        f"📜 **وضعیت {player.character_name}**\n\n"
        f"📖 کلاس: {player.get_class_info().get('emoji', '')} {player.get_class_info().get('name', '')}\n\n"
        f"❤️ **جون**: {player.stats.hp} / {player.stats.max_hp}\n"
        f"`{player.get_hp_bar()}`\n\n"
        f"📈 **اکس‌پی**: {player.stats.exp} / {player.stats.max_exp}\n"
        f"`{player.get_exp_bar()}`\n\n"
        f"⭐ **سطح**: {player.stats.level}\n"
        f"💰 **طلا**: {player.stats.gold}\n"
        f"⭐ **آپگرید پوینت**: {upgrade_points or 0}\n\n"
        f"⚔️ **قدرت اتک**: {player.stats.atk}\n"
        f"🛡️ **قدرت دفاع**: {player.stats.defense}\n"
        f"💨 **سرعت**: {player.stats.spd}\n"
        f"🍀 **شانس**: {player.stats.lck}\n"
    )
    
    # ===== اگه کاربر در حال ری‌اسپان هست =====
    respawn_time = await get_respawn_time(user_id)
    if respawn_time > 0:
        minutes = respawn_time // 60
        seconds = respawn_time % 60
        status_text += f"\n\n💀 **در حال ری‌اسپان**: {minutes}:{seconds:02d}"
    
    await update.message.reply_text(
        status_text,
        parse_mode="Markdown"
    )



async def status_persian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کامند فارسی 'وضعیت'"""
    await status(update, context)

