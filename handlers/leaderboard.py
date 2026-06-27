from handlers.panel_utils import register_panel
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_leaderboard_global, get_leaderboard_group,
    get_user_global_rank, get_user_group_rank,
    get_total_users_global, get_total_users_group,
    add_group_member, get_user
)
from models import Player
from config import CLASSES

# ========================================
# ایموجی کلاس‌ها
# ========================================
CLASS_EMOJIS = {
    "warrior": "🗡️",
    "samurai": "⚔️",
    "assassin": "🗡️",
    "paladin": "🛡️"
}

# ========================================
# توابع قفل پنل
# ========================================
# ========================================
# پنل اصلی لیدربرد
# ========================================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل اصلی لیدربرد"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # اضافه کردن کاربر به گروه برای لیدربرد گروهی
    if update.effective_chat.type in ["group", "supergroup"]:
        await add_group_member(user_id, chat_id)
    
    msg = (
        "🏆 **سالن مشاهیر شوالیه‌ها**\n\n"
        "اینجا می‌تونی رتبه‌ی خودت رو در بین سایر شوالیه‌ها ببینی.\n\n"
        "📊 **دسته‌بندی‌های رنکینگ:**\n"
        "💰 **ثروتمندترین‌ها**: بر اساس سکه\n"
        "⭐ **قوی‌ترین‌ها**: بر اساس لول\n"
        "⚔️ **قدرتمندترین‌ها**: بر اساس اتک + سلاح\n\n"
        "🌍 **نوع نمایش:**\n"
        "• گلوبال: همه شوالیه‌های سرزمین‌های میانی\n"
        "• گروهی: فقط شوالیه‌های همین گروه\n\n"
        "📈 **انتخاب کن:**"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💰 ثروتمندترین‌ها", callback_data="lb_gold", style="success"),
            InlineKeyboardButton("⭐ قوی‌ترین‌ها", callback_data="lb_level", style="primary"),
            InlineKeyboardButton("⚔️ قدرتمندترین‌ها", callback_data="lb_power", style="primary")
        ],
        [
            InlineKeyboardButton("🌍 گلوبال", callback_data="lb_type_global", style="primary"),
            InlineKeyboardButton("👥 گروهی", callback_data="lb_type_group", style="primary")
        ],
        [
            InlineKeyboardButton("📊 رتبه شخصی", callback_data="lb_my_rank", style="primary")
        ],
        [
            InlineKeyboardButton("🔙 بستن پنل", callback_data="lb_close", style="danger")
        ]
    ]
    
    _msg = await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    if _msg:
        register_panel(_msg.message_id, update.effective_user.id, context)

# ========================================
# نمایش لیدربرد
# ========================================
async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, stat_type: str, mode: str, page: int = 0):
    """نمایش لیدربرد بر اساس دسته و نوع"""
    query = update.callback_query
    await query.answer()
    
    
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    limit = 10
    offset = page * limit
    
    stat_names = {
        "gold": "ثروتمندترین شوالیه‌ها",
        "level": "قوی‌ترین شوالیه‌ها",
        "power": "قدرتمندترین شوالیه‌ها"
    }
    
    mode_names = {
        "global": "گلوبال",
        "group": "گروهی"
    }
    
    # دریافت داده‌ها
    if mode == "global":
        users = await get_leaderboard_global(stat_type, limit, offset)
        total_users = await get_total_users_global()
    else:
        users = await get_leaderboard_group(chat_id, stat_type, limit, offset)
        total_users = await get_total_users_group(chat_id)
    
    # ساخت پیام
    msg = f"🏆 **{stat_names.get(stat_type, 'رنکینگ')}** ({mode_names.get(mode, '')})\n\n"
    
    if not users:
        msg += "😔 هیچ شوالیه‌ای یافت نشد!"
    else:
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, user in enumerate(users):
            rank = offset + i + 1
            medal = medals[i] if i < len(medals) else f"{rank}."
            class_emoji = CLASS_EMOJIS.get(user['class'], "⚔️")
            
            if stat_type == "gold":
                value = f"{user['gold']:,} سکه"
            elif stat_type == "level":
                value = f"لول {user['level']}"
            elif stat_type == "power":
                # قدرت = اتک پایه + بونوس سلاح (ساده)
                value = f"{user['atk']} اتک"
            else:
                value = ""
            
            msg += f"{medal} {class_emoji} {user['character_name']} | {value}\n"
    
    # صفحه‌بندی
    total_pages = (total_users + limit - 1) // limit if total_users > 0 else 1
    current_page = page + 1
    
    keyboard = []
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"lb_page_{mode}_{stat_type}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"lb_page_{mode}_{stat_type}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت", callback_data="lb_back", style="primary")
    ])
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========================================
# رتبه شخصی
# ========================================
async def my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش رتبه شخصی کاربر"""
    query = update.callback_query
    await query.answer()
    
    
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await query.edit_message_text("❌ شما ثبت‌نام نکردید!")
        return
    
    # دریافت رتبه‌ها
    rank_gold_global = await get_user_global_rank(user_id, "gold")
    rank_level_global = await get_user_global_rank(user_id, "level")
    rank_power_global = await get_user_global_rank(user_id, "power")
    
    total_users_global = await get_total_users_global()
    
    # رتبه‌های گروهی
    if update.effective_chat.type in ["group", "supergroup"]:
        rank_gold_group = await get_user_group_rank(user_id, chat_id, "gold")
        rank_level_group = await get_user_group_rank(user_id, chat_id, "level")
        rank_power_group = await get_user_group_rank(user_id, chat_id, "power")
        total_users_group = await get_total_users_group(chat_id)
    else:
        rank_gold_group = 0
        rank_level_group = 0
        rank_power_group = 0
        total_users_group = 0
    
    class_emoji = CLASS_EMOJIS.get(player.class_key, "⚔️")
    
    msg = (
        f"📊 **رتبه شخصی تو**\n\n"
        f"🏰 شوالیه: {class_emoji} {player.character_name}\n"
        f"⭐ سطح: {player.stats.level}\n"
        f"💰 سکه: {player.stats.gold:,}\n"
        f"⚔️ اتک: {player.stats.atk}\n\n"
        f"🌍 **رتبه گلوبال:**\n"
        f"• سکه: #{rank_gold_global} از {total_users_global}\n"
        f"• لول: #{rank_level_global} از {total_users_global}\n"
        f"• قدرت: #{rank_power_global} از {total_users_global}\n"
    )
    
    if total_users_group > 0:
        msg += (
            f"\n👥 **رتبه گروهی:**\n"
            f"• سکه: #{rank_gold_group} از {total_users_group}\n"
            f"• لول: #{rank_level_group} از {total_users_group}\n"
            f"• قدرت: #{rank_power_group} از {total_users_group}\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data="lb_back", style="primary")]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========================================
# برگشت به پنل اصلی
# ========================================
async def lb_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برگشت به پنل اصلی لیدربرد"""
    query = update.callback_query
    await query.answer()
    
    
    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    
    # اضافه کردن کاربر به گروه
    if update.effective_chat.type in ["group", "supergroup"]:
        await add_group_member(user_id, chat_id)
    
    msg = (
        "🏆 **سالن مشاهیر شوالیه‌ها**\n\n"
        "اینجا می‌تونی رتبه‌ی خودت رو در بین سایر شوالیه‌ها ببینی.\n\n"
        "📊 **دسته‌بندی‌های رنکینگ:**\n"
        "💰 **ثروتمندترین‌ها**: بر اساس سکه\n"
        "⭐ **قوی‌ترین‌ها**: بر اساس لول\n"
        "⚔️ **قدرتمندترین‌ها**: بر اساس اتک + سلاح\n\n"
        "🌍 **نوع نمایش:**\n"
        "• گلوبال: همه شوالیه‌های سرزمین‌های میانی\n"
        "• گروهی: فقط شوالیه‌های همین گروه\n\n"
        "📈 **انتخاب کن:**"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💰 ثروتمندترین‌ها", callback_data="lb_gold", style="success"),
            InlineKeyboardButton("⭐ قوی‌ترین‌ها", callback_data="lb_level", style="primary"),
            InlineKeyboardButton("⚔️ قدرتمندترین‌ها", callback_data="lb_power", style="primary")
        ],
        [
            InlineKeyboardButton("🌍 گلوبال", callback_data="lb_type_global", style="primary"),
            InlineKeyboardButton("👥 گروهی", callback_data="lb_type_group", style="primary")
        ],
        [
            InlineKeyboardButton("📊 رتبه شخصی", callback_data="lb_my_rank", style="primary")
        ],
        [
            InlineKeyboardButton("🔙 بستن پنل", callback_data="lb_close", style="danger")
        ]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ========================================
# بستن پنل
# ========================================
async def lb_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن پنل لیدربرد"""
    query = update.callback_query
    await query.answer()
    
    
    await query.delete_message()

