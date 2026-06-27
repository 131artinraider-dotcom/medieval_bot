from handlers.panel_utils import register_panel
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_user, get_user_quests, update_quest_progress,
    claim_quest_reward, claim_all_quests, get_quest_time_remaining,
    QUEST_TYPES, DIFFICULTY_NAMES, reset_daily_quests
)
from models import Player

# ========================================
# پنل اصلی دیلی کوئست
# ========================================
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پنل دیلی کوئست"""
    user_id = update.effective_user.id
    
    # ریست خودکار کوئست‌های قدیمی
    await reset_daily_quests()
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await update.message.reply_text(
            "❌ شما هنوز شخصیت خودت رو نساختی!\n"
            "برای شروع از /start یا 'شروع' استفاده کن.",
            parse_mode="Markdown"
        )
        return
    
    # دریافت کوئست‌ها
    quests = await get_user_quests(user_id)
    
    if not quests:
        await update.message.reply_text(
            "❌ مشکلی در تولید کوئست‌ها وجود دارد!",
            parse_mode="Markdown"
        )
        return
    
    # زمان باقی‌مونده تا ریست
    remaining = await get_quest_time_remaining()
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    seconds = remaining % 60
    
    msg = (
        f"📋 **ماموریت‌های روزانه**\n\n"
        f"⏱️ زمان تا ریست بعدی: {hours:02d}:{minutes:02d}:{seconds:02d}\n\n"
        f"📌 **ماموریت‌های امروز:**\n\n"
    )
    
    completed_count = 0
    keyboard = []
    
    for i, quest in enumerate(quests):
        difficulty = quest['quest_difficulty']
        diff_name = DIFFICULTY_NAMES.get(difficulty, "🟡")
        
        quest_info = QUEST_TYPES.get(quest['quest_type'], {})
        quest_name = quest_info.get('name', quest['quest_type'])
        quest_emoji = quest_info.get('emoji', '📌')
        
        progress = quest['quest_progress']
        target = quest['quest_target']
        
        # ساخت نوار پیشرفت (۱۰ خونه)
        filled = int((progress / target) * 10)
        if filled > 10:
            filled = 10
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        
        completed = quest['quest_completed']
        status = "✅" if completed else "⏳"
        
        if completed:
            completed_count += 1
        
        msg += (
            f"{status} **{diff_name}:** {quest_emoji} {quest_name}\n"
            f"   پیشرفت: {bar} {progress}/{target}\n"
            f"   🎁 جایزه: {quest['quest_reward_gold']} سکه + {quest['quest_reward_upgrade']} آپگرید\n\n"
        )
        
        # دکمه دریافت جایزه برای کوئست‌های کامل شده
        if completed:
            keyboard.append([
                InlineKeyboardButton(
                    f"🎁 دریافت {quest_name}",
                    callback_data=f"daily_claim_{quest['id']}",
                    style="success"
                )
            ])
    
    # دکمه دریافت همه جایزه‌ها
    if completed_count > 0:
        keyboard.append([
            InlineKeyboardButton(
                f"🎁 دریافت همه جایزه‌ها ({completed_count})",
                callback_data="daily_claim_all",
                style="success"
            )
        ])
    
    # دکمه بستن پنل
    keyboard.append([
        InlineKeyboardButton("🔙 بستن پنل", callback_data="daily_close", style="danger")
    ])
    
    _msg = await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    if _msg:
        register_panel(_msg.message_id, update.effective_user.id, context)

# ========================================
# دریافت جایزه یک کوئست
# ========================================
async def daily_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت جایزه یک کوئست"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    quest_id = int(data.replace("daily_claim_", ""))
    
    print(f"🔍 دریافت جایزه کوئست {quest_id} برای کاربر {user_id}")
    
    result = await claim_quest_reward(user_id, quest_id)
    
    if not result["success"]:
        await query.edit_message_text(
            f"❌ {result['message']}",
            parse_mode="Markdown"
        )
        return
    
    await query.edit_message_text(
        f"✅ **جایزه دریافت شد!**\n\n"
        f"🎁 {result['gold']} سکه + {result['upgrade']} آپگرید پوینت\n"
        f"📌 برای {result['quest_name']}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت به ماموریت‌ها", callback_data="daily_back", style="primary")]
        ]),
        parse_mode="Markdown"
    )

# ========================================
# دریافت همه جایزه‌ها
# ========================================
async def daily_claim_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت همه جایزه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    print(f"🔍 دریافت همه جایزه‌ها برای کاربر {user_id}")
    
    result = await claim_all_quests(user_id)
    
    if not result["success"]:
        await query.edit_message_text(
            f"❌ {result['message']}",
            parse_mode="Markdown"
        )
        return
    
    await query.edit_message_text(
        f"✅ **همه جایزه‌ها دریافت شد!**\n\n"
        f"🎁 {result['gold']} سکه + {result['upgrade']} آپگرید پوینت\n"
        f"📌 {result['count']} کوئست کامل شد!\n"
        f"📋 {', '.join(result['quest_names'])}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت به ماموریت‌ها", callback_data="daily_back", style="primary")]
        ]),
        parse_mode="Markdown"
    )

# ========================================
# برگشت به پنل اصلی
# ========================================
async def daily_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برگشت به پنل دیلی کوئست"""
    query = update.callback_query
    await query.answer()
    
    await daily(update, context)

# ========================================
# بستن پنل
# ========================================
async def daily_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن پنل دیلی کوئست"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()

