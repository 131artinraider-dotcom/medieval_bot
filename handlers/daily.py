from handlers.panel_utils import register_panel
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_user, get_user_quests, claim_quest_reward,
    claim_all_quests, get_quest_time_remaining,
    QUEST_TYPES, DIFFICULTY_NAMES, reset_daily_quests
)
from models import Player

# رنگ دکمه‌ها با ایموجی بر اساس سختی
DIFF_BUTTON_EMOJI = {
    "easy": "🟢",
    "medium": "🟡",
    "hard": "🔴"
}

async def _build_daily_panel(user_id: int):
    quests = await get_user_quests(user_id)
    if not quests:
        return None, None

    remaining = await get_quest_time_remaining()
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    seconds = remaining % 60

    msg = (
        f"📋 **ماموریت‌های روزانه**\n\n"
        f"⏱️ ریست بعدی: {hours:02d}:{minutes:02d}:{seconds:02d}\n\n"
    )

    keyboard = []
    completed_count = 0

    for quest in quests:
        difficulty = quest['quest_difficulty']
        diff_name = DIFFICULTY_NAMES.get(difficulty, "🟡")
        diff_emoji = DIFF_BUTTON_EMOJI.get(difficulty, "🟡")
        quest_info = QUEST_TYPES.get(quest['quest_type'], {})
        quest_name = quest_info.get('name', quest['quest_type'])
        quest_emoji = quest_info.get('emoji', '📌')

        progress = quest['quest_progress']
        target = quest['quest_target']
        filled = min(int((progress / target) * 8), 8)
        bar = "█" * filled + "░" * (8 - filled)
        completed = quest['quest_completed']
        status = "✅" if completed else "⏳"

        if completed:
            completed_count += 1

        msg += (
            f"{status} {diff_emoji} **{quest_name}** ({diff_name})\n"
            f"   {quest_emoji} {bar} {progress}/{target}\n"
            f"   🎁 {quest['quest_reward_gold']} سکه + {quest['quest_reward_upgrade']} آپگرید\n\n"
        )

        if completed:
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ دریافت {diff_emoji} {quest_name}",
                    callback_data=f"daily_claim_{quest['id']}",
                    style="success"
                )
            ])

    if completed_count > 1:
        keyboard.append([
            InlineKeyboardButton(
                f"🎁 دریافت همه ({completed_count} ماموریت)",
                callback_data="daily_claim_all",
                style="success"
            )
        ])

    keyboard.append([InlineKeyboardButton("🔙 بستن", callback_data="daily_close", style="danger")])
    return msg, keyboard


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await reset_daily_quests()

    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    if not player or not player.is_registered:
        await update.message.reply_text("❌ هنوز ثبت‌نام نکردی! از /start شروع کن.")
        return

    msg, keyboard = await _build_daily_panel(user_id)
    if not msg:
        await update.message.reply_text("❌ مشکلی در تولید کوئست‌ها وجود دارد!")
        return

    _msg = await update.message.reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    if _msg:
        register_panel(_msg.message_id, user_id, context, update.effective_chat.id)


async def daily_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    quest_id = int(query.data.replace("daily_claim_", ""))
    result = await claim_quest_reward(user_id, quest_id)

    if not result["success"]:
        await query.edit_message_text(f"❌ {result['message']}", parse_mode="Markdown")
        return

    await query.edit_message_text(
        f"✅ **جایزه دریافت شد!**\n\n"
        f"🎁 {result['gold']} سکه + {result['upgrade']} آپگرید\n"
        f"📌 برای: {result['quest_name']}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت به ماموریت‌ها", callback_data="daily_back", style="primary")]
        ]),
        parse_mode="Markdown"
    )


async def daily_claim_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    result = await claim_all_quests(user_id)

    if not result["success"]:
        await query.edit_message_text(f"❌ {result['message']}", parse_mode="Markdown")
        return

    await query.edit_message_text(
        f"✅ **همه جایزه‌ها دریافت شد!**\n\n"
        f"🎁 {result['gold']} سکه + {result['upgrade']} آپگرید\n"
        f"📌 {result['count']} کوئست: {', '.join(result['quest_names'])}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت", callback_data="daily_back", style="primary")]
        ]),
        parse_mode="Markdown"
    )


async def daily_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    msg, keyboard = await _build_daily_panel(user_id)
    if not msg:
        await query.edit_message_text("❌ مشکلی پیش اومد!")
        return
    await query.edit_message_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def daily_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except Exception:
        pass
