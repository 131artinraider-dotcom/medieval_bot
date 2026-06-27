from handlers.panel_utils import register_panel
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user, get_user_upgrade_info, apply_upgrade, get_upgrade_cost, update_quest_progress
from models import Player
from config import ITEM_STATS

def create_bar(current, max_val, length=15):
    if max_val <= 0:
        return "░" * length
    filled = int((current / max_val) * length)
    if filled > length:
        filled = length
    empty = length - filled
    return "█" * filled + "░" * empty

STAT_EMOJIS = {
    "hp": "❤️",
    "atk": "⚔️",
    "def": "🛡️",
    "spd": "💨",
    "lck": "🍀"
}

STAT_NAMES = {
    "hp": "جون",
    "atk": "اتک",
    "def": "دفاع",
    "spd": "سرعت",
    "lck": "شانس"
}

STAT_BONUS = {
    "hp": 150,
    "atk": 2,
    "def": 2,
    "spd": 2,
    "lck": 2
}

# ===== پنل اصلی آپگرید =====
async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پنل آپگرید"""
    user_id = update.effective_user.id
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await update.message.reply_text(
            "❌ شما هنوز شخصیت خودت رو نساختی!\n"
            "برای شروع از /start یا 'شروع' استفاده کن.",
            parse_mode="Markdown"
        )
        return
    
    # دریافت اطلاعات آپگرید
    info = await get_user_upgrade_info(user_id)
    
    upgrade_points = info['upgrade_points'] or 0
    total_upgrades = info['total_upgrades'] or 0
    cost = get_upgrade_cost(total_upgrades)
    
    # ساخت پیام
    msg = (
        f"⭐ **آپگرید** | پوینت: {upgrade_points} | هزینه: {cost}\n"
        f"❤️ {player.stats.hp}/{player.stats.max_hp} `{create_bar(player.stats.hp, player.stats.max_hp)}`\n"
        f"⚔️{player.stats.atk}(Lv{info['atk_level']}) 🛡️{player.stats.defense}(Lv{info['def_level']}) 💨{player.stats.spd}(Lv{info['spd_level']}) 🍀{player.stats.lck}(Lv{info['lck_level']})\n"
        f"انتخاب کن:"
    )
    
    keyboard = []
    
    for stat, emoji in STAT_EMOJIS.items():
        stat_name = STAT_NAMES[stat]
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {stat_name} ({cost} پوینت)",
                callback_data=f"upgrade_{stat}",

                style="success" if stat == "hp" else "primary"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 بستن پنل", callback_data="upgrade_close", style="danger")
    ])
    
    _msg = await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    if _msg:
        register_panel(_msg.message_id, update.effective_user.id, context)


# ===== اجرای آپگرید =====
async def execute_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای آپگرید روی استت انتخاب شده"""
    query = update.callback_query
    await query.answer()
    
    
    data = query.data
    stat_type = data.replace("upgrade_", "")
    
    user_id = query.from_user.id
    
    # اعمال آپگرید
    result = await apply_upgrade(user_id, stat_type)
    
    if not result["success"]:
        await query.edit_message_text(
            f"❌ {result['message']}",
            parse_mode="Markdown"
        )
        return
    
    # ===== آپدیت پیشرفت کوئست =====
    await update_quest_progress(user_id, "upgrade")
    
    # دریافت اطلاعات جدید برای نمایش
    info = await get_user_upgrade_info(user_id)
    
    # ساخت پیام موفقیت
    emoji = STAT_EMOJIS[stat_type]
    name = STAT_NAMES[stat_type]
    
    # محاسبه نوار جون جدید (اگه hp باشه)
    bar = ""
    if stat_type == "hp":
        bar = f"\n`{create_bar(result['new_hp'], result['new_max_hp'])}`"
    
    msg = (
        f"✅ **آپگرید انجام شد!**\n\n"
        f"{emoji} **{name}** → لول {result['new_level']}\n"
        f"💰 هزینه: {result['cost']} پوینت\n"
        f"📈 مقدار جدید: {result['new_value']}\n"
        f"{bar}\n\n"
        f"💰 پوینت باقی‌مونده: {info['upgrade_points']}\n"
        f"📊 کل آپگریدها: {info['total_upgrades']}\n"
        f"💡 هزینه بعدی: {get_upgrade_cost(info['total_upgrades'])} پوینت"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت به پنل آپگرید", callback_data="upgrade_back", style="primary")]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )





# ===== برگشت به پنل آپگرید =====
async def upgrade_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برگشت به پنل آپگرید"""
    query = update.callback_query
    await query.answer()
    
    
    
    user_id = query.from_user.id
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await query.edit_message_text("❌ شما ثبت‌نام نکردید!")
        return
    
    info = await get_user_upgrade_info(user_id)
    
    upgrade_points = info['upgrade_points'] or 0
    total_upgrades = info['total_upgrades'] or 0
    cost = get_upgrade_cost(total_upgrades)
    
    msg = (
        f"⭐ **آپگرید** | پوینت: {upgrade_points} | هزینه: {cost}\n"
        f"❤️ {player.stats.hp}/{player.stats.max_hp} `{create_bar(player.stats.hp, player.stats.max_hp)}`\n"
        f"⚔️{player.stats.atk}(Lv{info['atk_level']}) 🛡️{player.stats.defense}(Lv{info['def_level']}) 💨{player.stats.spd}(Lv{info['spd_level']}) 🍀{player.stats.lck}(Lv{info['lck_level']})\n"
        f"انتخاب کن:"
    )
    
    keyboard = []
    
    for stat, emoji in STAT_EMOJIS.items():
        stat_name = STAT_NAMES[stat]
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {stat_name} ({cost} پوینت)",
                callback_data=f"upgrade_{stat}",
                style="success" if stat == "hp" else "primary"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 بستن پنل", callback_data="upgrade_close", style="danger")
    ])
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== بستن پنل =====
async def upgrade_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن پنل آپگرید"""
    query = update.callback_query
    await query.answer()
    
    
    await query.delete_message()

