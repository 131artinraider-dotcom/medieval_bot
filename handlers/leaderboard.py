from handlers.panel_utils import register_panel
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

CLASS_EMOJIS = {
    "warrior": "🗡️",
    "samurai": "⚔️",
    "assassin": "🥷",
    "paladin": "🛡️"
}

MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if update.effective_chat.type in ["group", "supergroup"]:
        await add_group_member(user_id, chat_id)

    # حالت پیش‌فرض
    context.user_data['lb_mode'] = 'global'

    keyboard = [
        [
            InlineKeyboardButton("💰 سکه", callback_data="lb_gold"),
            InlineKeyboardButton("⭐ لول", callback_data="lb_level"),
            InlineKeyboardButton("⚔️ قدرت", callback_data="lb_power"),
        ],
        [
            InlineKeyboardButton("🌍 گلوبال", callback_data="lb_type_global"),
            InlineKeyboardButton("👥 گروهی", callback_data="lb_type_group"),
        ],
        [InlineKeyboardButton("📊 رتبه من", callback_data="lb_my_rank")],
        [InlineKeyboardButton("❌ بستن", callback_data="lb_close")],
    ]

    _msg = await update.message.reply_text(
        "🏆 **سالن مشاهیر**\n\n"
        "دسته و نوع نمایش رو انتخاب کن:\n\n"
        "🌍 گلوبال = همه بازیکنان\n"
        "👥 گروهی = فقط اعضای این گروه",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    if _msg:
        register_panel(_msg.message_id, user_id, context)


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, stat_type: str, mode: str, page: int = 0):
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    limit = 10
    offset = page * limit

    stat_titles = {"gold": "💰 ثروتمندترین‌ها", "level": "⭐ قوی‌ترین‌ها", "power": "⚔️ قدرتمندترین‌ها"}
    mode_names = {"global": "🌍 گلوبال", "group": "👥 گروهی"}

    if mode == "global":
        users = await get_leaderboard_global(stat_type, limit, offset)
        total_users = await get_total_users_global()
    else:
        users = await get_leaderboard_group(chat_id, stat_type, limit, offset)
        total_users = await get_total_users_group(chat_id)

    title = f"{stat_titles.get(stat_type, '🏆 رنکینگ')} | {mode_names.get(mode, '')}"
    msg = f"{title}\n" + "─" * 28 + "\n"

    if not users:
        msg += "\n😔 کسی پیدا نشد!\n"
        if mode == "group":
            msg += "💡 اعضا باید یک‌بار /leaderboard بزنن تا ثبت بشن."
    else:
        for i, user in enumerate(users):
            rank = offset + i + 1
            medal = MEDALS[i] if i < len(MEDALS) else f"{rank}."
            cls = CLASS_EMOJIS.get(user['class'], "⚔️")
            name = user['character_name']

            if stat_type == "gold":
                val = f"{user['gold']:,}🪙"
            elif stat_type == "level":
                val = f"Lv.{user['level']}"
            else:
                val = f"{user['atk']}⚔️"

            msg += f"{medal} {cls} `{name:<12}` {val}\n"

    total_pages = max(1, (total_users + limit - 1) // limit)
    msg += f"\n📄 صفحه {page + 1}/{total_pages} | {total_users} بازیکن"

    keyboard = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"lb_page_{mode}_{stat_type}_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"lb_page_{mode}_{stat_type}_{page + 1}"))
    if nav:
        keyboard.append(nav)

    keyboard.append([
        InlineKeyboardButton("💰", callback_data=f"lb_page_{mode}_gold_0"),
        InlineKeyboardButton("⭐", callback_data=f"lb_page_{mode}_level_0"),
        InlineKeyboardButton("⚔️", callback_data=f"lb_page_{mode}_power_0"),
    ])
    keyboard.append([
        InlineKeyboardButton("🌍 گلوبال", callback_data="lb_type_global"),
        InlineKeyboardButton("👥 گروهی", callback_data="lb_type_group"),
    ])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="lb_back")])

    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = update.effective_chat.id

    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    if not player or not player.is_registered:
        await query.edit_message_text("❌ ثبت‌نام نکردی!")
        return

    rg = await get_user_global_rank(user_id, "gold")
    rl = await get_user_global_rank(user_id, "level")
    rp = await get_user_global_rank(user_id, "power")
    total_g = await get_total_users_global()

    cls = CLASS_EMOJIS.get(player.class_key, "⚔️")
    msg = (
        f"📊 **رتبه شخصی**\n\n"
        f"{cls} **{player.character_name}** | Lv.{player.stats.level}\n"
        f"─────────────────\n"
        f"🌍 **گلوبال** (از {total_g} نفر)\n"
        f"  💰 سکه: #{rg}\n"
        f"  ⭐ لول: #{rl}\n"
        f"  ⚔️ قدرت: #{rp}\n"
    )

    if update.effective_chat.type in ["group", "supergroup"]:
        rgg = await get_user_group_rank(user_id, chat_id, "gold")
        rgl = await get_user_group_rank(user_id, chat_id, "level")
        rgp = await get_user_group_rank(user_id, chat_id, "power")
        total_gr = await get_total_users_group(chat_id)
        msg += (
            f"\n👥 **گروهی** (از {total_gr} نفر)\n"
            f"  💰 سکه: #{rgg}\n"
            f"  ⭐ لول: #{rgl}\n"
            f"  ⚔️ قدرت: #{rgp}\n"
        )

    keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="lb_back")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def lb_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ["group", "supergroup"]:
        await add_group_member(user_id, chat_id)

    keyboard = [
        [
            InlineKeyboardButton("💰 سکه", callback_data="lb_gold"),
            InlineKeyboardButton("⭐ لول", callback_data="lb_level"),
            InlineKeyboardButton("⚔️ قدرت", callback_data="lb_power"),
        ],
        [
            InlineKeyboardButton("🌍 گلوبال", callback_data="lb_type_global"),
            InlineKeyboardButton("👥 گروهی", callback_data="lb_type_group"),
        ],
        [InlineKeyboardButton("📊 رتبه من", callback_data="lb_my_rank")],
        [InlineKeyboardButton("❌ بستن", callback_data="lb_close")],
    ]

    await query.edit_message_text(
        "🏆 **سالن مشاهیر**\n\n"
        "دسته و نوع نمایش رو انتخاب کن:\n\n"
        "🌍 گلوبال = همه بازیکنان\n"
        "👥 گروهی = فقط اعضای این گروه",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def lb_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except Exception:
        pass
