import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_user, get_db, get_inventory, get_equipped,
    start_dungeon, get_dungeon, update_dungeon_hp,
    update_dungeon_stage, end_dungeon, player_died,
    is_player_dead, get_respawn_time, get_cooldown_remaining,
    add_item_to_inventory, update_user_hp, use_consumable,
    check_respawn, add_exp, check_active_dungeon,
    apply_weapon_bonus, set_bleed, get_bleed, clear_bleed,
    update_quest_progress
)
from models import Player, Item
from config import DUNGEONS, ITEM_STATS
from handlers.callbacks import check_ownership, set_panel_owner, clear_panel_owner

def create_bar(current, max_val, length=15):
    if max_val <= 0:
        return "░" * length
    filled = int((current / max_val) * length)
    if filled > length:
        filled = length
    empty = length - filled
    return "█" * filled + "░" * empty

# ==========================================
# پنل اصلی دانجن‌ها
# ==========================================
async def dungeon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پنل اصلی دانجن‌ها"""
    user_id = update.effective_user.id
    
    await check_respawn(user_id)
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await update.message.reply_text(
            "❌ شما هنوز شخصیت خودت رو نساختی!\n"
            "برای شروع از /start یا 'شروع' استفاده کن.",
            parse_mode="Markdown"
        )
        return
    
    if await check_active_dungeon(user_id):
        await update.message.reply_text(
            "⚠️ **شما در حال حاضر یک دانجن فعال دارید!**\n"
            "قبل از شروع ماموریت جدید، ماموریت فعلی رو تموم کن.",
            parse_mode="Markdown"
        )
        return
    
    if await is_player_dead(user_id):
        respawn_time = await get_respawn_time(user_id)
        minutes = respawn_time // 60
        seconds = respawn_time % 60
        await update.message.reply_text(
            f"💀 **شما در نبرد به شهادت رسیدی!**\n\n"
            f"⏱️ زمان تا ری‌اسپان: {minutes}:{seconds:02d}\n\n"
            f"تا اون زمان نمی‌تونی وارد دانجن بشی.\n"
            f"بعد از ری‌اسپان، جون تو نصف میشه.",
            parse_mode="Markdown"
        )
        return
    
    msg = (
        "🏰 **سالن ماموریت‌های شوالیه‌ها**\n\n"
        "به سالن ماموریت‌ها خوش آمدی، شوالیه! \n"
        "شهروندان برای نجات سرزمین‌شان از دست هیولاها به کمک نیاز دارند.\n"
        "هر ماموریت پاداش‌های مخصوص خودش رو داره.\n\n"
        "📋 **ماموریت‌های موجود:**\n"
    )
    
    keyboard = []
    
    for key, dungeon_data in DUNGEONS.items():
        cooldown = await get_cooldown_remaining(user_id, key)
        level_required = dungeon_data.get('level_required', 0)
        can_access = player.stats.level >= level_required
        
        status = ""
        if cooldown > 0:
            minutes = cooldown // 60
            seconds = cooldown % 60
            status = f" ⏱️ {minutes}:{seconds:02d}"
        elif not can_access:
            status = f" 🔒 نیاز: لول {level_required}"
        
        btn_text = f"{dungeon_data['emoji']} {dungeon_data['name']}{status}"
        
        if not can_access:
            callback = "dungeon_level_locked"
        elif cooldown > 0:
            callback = "dungeon_locked"
        else:
            callback = f"dungeon_start_{key}"
        
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback, style="primary")])
    
    keyboard.append([InlineKeyboardButton("🔙 بستن پنل", callback_data="dungeon_close", style="danger")])
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==========================================
# پنل شروع دانجن
# ==========================================
async def dungeon_start_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, dungeon_type: str):
    """نمایش اطلاعات دانجن قبل از شروع"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    user_id = query.from_user.id
    
    if await check_active_dungeon(user_id):
        await query.edit_message_text(
            "⚠️ **شما در حال حاضر یک دانجن فعال دارید!**\n"
            "قبل از شروع ماموریت جدید، ماموریت فعلی رو تموم کن.",
            parse_mode="Markdown"
        )
        return
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await query.edit_message_text("❌ شما ثبت‌نام نکردید!")
        return
    
    dungeon_data = DUNGEONS.get(dungeon_type)
    if not dungeon_data:
        await query.edit_message_text("❌ دانجن نامعتبر!")
        return
    
    equipped = await get_equipped(user_id)
    equipped_weapon = next((Item(**dict(item)) for item in equipped if item['item_type'] == 'weapon'), None)
    equipped_armor = next((Item(**dict(item)) for item in equipped if item['item_type'] == 'armor'), None)
    
    conn = await get_db()
    upgrade_points = await conn.fetchval("SELECT upgrade_points FROM users WHERE user_id = $1", user_id)
    await conn.close()
    
    atk_bonus = 0
    weapon_name = "هیچ"
    if equipped_weapon:
        weapon_name = equipped_weapon.item_name
        weapon_stats = ITEM_STATS.get('weapon', {}).get(weapon_name, {})
        atk_bonus = weapon_stats.get('atk_bonus', 0)
    
    def_bonus = 0
    armor_name = "هیچ"
    if equipped_armor:
        armor_name = equipped_armor.item_name
        armor_stats = ITEM_STATS.get('armor', {}).get(armor_name, {})
        def_bonus = armor_stats.get('def_bonus', 0)
    
    msg = (
        f"{dungeon_data['emoji']} **{dungeon_data['name']}**\n\n"
        f"📖 **توضیحات ماموریت:**\n"
        f"{dungeon_data.get('description', 'ماموریتی برای نابودی هیولاها')}\n\n"
        f"🛡️ **تجهیزات تو:**\n"
        f"🗡️ سلاح: {weapon_name} (+{atk_bonus} اتک)\n"
        f"🛡️ زره: {armor_name} (+{def_bonus} دفاع)\n\n"
        f"📊 **اطلاعات ماموریت:**\n"
        f"📍 مراحل: {dungeon_data['stages']} مرحله\n"
        f"📍 نیاز: لول {dungeon_data.get('level_required', 0)}\n\n"
        f"🎁 **پاداش‌ها:**\n"
        f"💰 {dungeon_data['base_reward_gold']} سکه\n"
        f"⭐ {dungeon_data['base_reward_upgrade']} آپگرید پوینت\n"
        f"✨ {dungeon_data['base_reward_exp']} تجربه\n\n"
        f"🎲 **احتمال دراپ آیتم از هر مرحله:**\n"
    )
    
    for item in dungeon_data['drop_items']:
        chance_percent = int(item['chance'] * 100)
        msg += f"   • {item['name']} ({chance_percent}%)\n"
    
    msg += (
        f"\n⭐ **آپگرید پوینت‌های تو:** {upgrade_points or 0}\n"
        f"❤️ **جون تو:** {player.stats.hp} / {player.stats.max_hp}\n"
        f"`{create_bar(player.stats.hp, player.stats.max_hp)}`"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚔️ شروع ماموریت", callback_data=f"dungeon_battle_start_{dungeon_type}", style="success")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="dungeon_back", style="danger")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==========================================
# شروع نبرد
# ==========================================
async def dungeon_battle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع نبرد در دانجن"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    user_id = query.from_user.id
    
    dungeon_type = query.data.replace("dungeon_battle_start_", "")
    
    if await check_active_dungeon(user_id):
        await query.edit_message_text(
            "⚠️ **شما در حال حاضر یک دانجن فعال دارید!**\n"
            "قبل از شروع ماموریت جدید، ماموریت فعلی رو تموم کن.",
            parse_mode="Markdown"
        )
        return
    
    started = await start_dungeon(user_id, dungeon_type)
    
    if not started:
        await query.edit_message_text(
            "⚠️ **مشکل در شروع دانجن!**\n"
            "لطفاً دوباره تلاش کن.",
            parse_mode="Markdown"
        )
        return
    
    await dungeon_battle_round(update, context, dungeon_type)

# ==========================================
# یک راند نبرد
# ==========================================
async def dungeon_battle_round(update: Update, context: ContextTypes.DEFAULT_TYPE, dungeon_type: str):
    """نمایش یک راند نبرد"""
    query = update.callback_query
    if query:
        await query.answer()
        if not await check_ownership(update, context):
            return
        await set_panel_owner(update, context)
    
    user_id = update.effective_user.id if update.effective_user else query.from_user.id
    
    dungeon = await get_dungeon(user_id)
    if not dungeon:
        if query:
            await query.edit_message_text("❌ دانجن فعالی وجود ندارد!")
        return
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    if not player:
        return
    
    dungeon_data = DUNGEONS.get(dungeon_type)
    if not dungeon_data:
        return
    
    equipped = await get_equipped(user_id)
    equipped_weapon = next((Item(**dict(item)) for item in equipped if item['item_type'] == 'weapon'), None)
    equipped_armor = next((Item(**dict(item)) for item in equipped if item['item_type'] == 'armor'), None)
    
    atk_bonus = 0
    weapon_name = "هیچ"
    if equipped_weapon:
        weapon_name = equipped_weapon.item_name
        weapon_stats = ITEM_STATS.get('weapon', {}).get(weapon_name, {})
        atk_bonus = weapon_stats.get('atk_bonus', 0)
    
    def_bonus = 0
    armor_name = "هیچ"
    if equipped_armor:
        armor_name = equipped_armor.item_name
        armor_stats = ITEM_STATS.get('armor', {}).get(armor_name, {})
        def_bonus = armor_stats.get('def_bonus', 0)
    
    total_atk = player.stats.atk + atk_bonus
    total_def = player.stats.defense + def_bonus
    
    current_hp = dungeon['current_hp'] or player.stats.hp
    enemy_hp = dungeon['enemy_hp']
    stage = dungeon['stage']
    total_stages = dungeon_data['stages']
    
    if current_hp <= 0:
        await player_died(user_id)
        if query:
            await query.edit_message_text(
                f"💀 **تو در نبرد با {dungeon_data['name']} به شهادت رسیدی!**\n\n"
                f"⏱️ تا ۱ ساعت دیگه ری‌اسپان میشی.\n"
                f"بعد از ری‌اسپان، جون تو نصف میشه.\n\n"
                f"از کامند /status برای مشاهده زمان باقی‌مونده استفاده کن.",
                parse_mode="Markdown"
            )
        return
    
    msg = (
        f"⚔️ **نبرد با {dungeon_data['name']}** (مرحله {stage}/{total_stages})\n\n"
        f"🛡️ **تجهیزات تو:**\n"
        f"🗡️ سلاح: {weapon_name} (+{atk_bonus} اتک)\n"
        f"🛡️ زره: {armor_name} (+{def_bonus} دفاع)\n\n"
        f"📊 **وضعیت نبرد:**\n\n"
        f"❤️ **تو:** {current_hp} / {player.stats.max_hp}\n"
        f"`{create_bar(current_hp, player.stats.max_hp)}`\n\n"
        f"🗡️ **{dungeon_data['name']}:** {enemy_hp} / {dungeon_data['enemy_hp']}\n"
        f"`{create_bar(enemy_hp, dungeon_data['enemy_hp'])}`"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚔️ حمله", callback_data="dungeon_attack", style="success")],
        [InlineKeyboardButton("🏃 فرار", callback_data="dungeon_flee", style="danger")],
        [InlineKeyboardButton("🧪 استفاده پوشن", callback_data="dungeon_potion", style="primary")]
    ]
    
    if query:
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==========================================
# حمله پلیر
# ==========================================
async def dungeon_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای حمله پلیر با سیستم بونوس کامل"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    user_id = query.from_user.id
    
    dungeon = await get_dungeon(user_id)
    if not dungeon:
        await query.edit_message_text("❌ دانجن فعالی وجود ندارد!")
        return
    
    dungeon_type = dungeon['dungeon_type']
    dungeon_data = DUNGEONS.get(dungeon_type)
    if not dungeon_data:
        await query.edit_message_text("❌ دانجن نامعتبر!")
        return
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    if not player:
        return
    
    equipped = await get_equipped(user_id)
    equipped_weapon = next((Item(**dict(item)) for item in equipped if item['item_type'] == 'weapon'), None)
    equipped_armor = next((Item(**dict(item)) for item in equipped if item['item_type'] == 'armor'), None)
    
    atk_bonus = 0
    weapon_name = "هیچ"
    if equipped_weapon:
        weapon_name = equipped_weapon.item_name
        weapon_stats = ITEM_STATS.get('weapon', {}).get(weapon_name, {})
        atk_bonus = weapon_stats.get('atk_bonus', 0)
    
    def_bonus = 0
    armor_name = "هیچ"
    if equipped_armor:
        armor_name = equipped_armor.item_name
        armor_stats = ITEM_STATS.get('armor', {}).get(armor_name, {})
        def_bonus = armor_stats.get('def_bonus', 0)
    
    total_atk = player.stats.atk + atk_bonus
    total_def = player.stats.defense + def_bonus
    
    current_hp = dungeon['current_hp'] or player.stats.hp
    enemy_hp = dungeon['enemy_hp']
    enemy_def = dungeon_data['enemy_def']
    enemy_atk = dungeon_data['enemy_atk']
    
    # ===== محاسبه دمیج پایه =====
    player_damage = total_atk - enemy_def
    if player_damage < 1:
        player_damage = 1
    
    # ===== اعمال بونوس سلاح =====
    bonus_result = await apply_weapon_bonus(user_id, player_damage, enemy_hp, enemy_def)
    player_damage = bonus_result['damage']
    bonus_messages = []
    
    if bonus_result.get('message'):
        bonus_messages.append(bonus_result['message'])
    
    # ===== لایف استیل (خون‌آشامی) =====
    lifesteal_amount = bonus_result.get('extra_effects', {}).get('lifesteal', 0)
    if lifesteal_amount > 0:
        current_hp = min(current_hp + lifesteal_amount, player.stats.max_hp)
        await update_user_hp(user_id, current_hp)
        await update_dungeon_hp(user_id, current_hp, enemy_hp)
        bonus_messages.append(f"🩸 **لایف استیل!** +{lifesteal_amount} جون")
    
    # ===== خونریزی (زخم عمیق) - از دیتابیس =====
    bleed_amount = await get_bleed(user_id)
    total_damage_dealt = player_damage
    
    if bleed_amount > 0:
        enemy_hp -= bleed_amount
        if enemy_hp < 0:
            enemy_hp = 0
        await update_dungeon_hp(user_id, current_hp, enemy_hp)
        bonus_messages.append(f"🩸 **خونریزی!** -{bleed_amount} جون از زخم عمیق")
        total_damage_dealt = player_damage + bleed_amount
    
    # ===== ذخیره خونریزی جدید (انباشته شدن) =====
    new_bleed = bonus_result.get('extra_effects', {}).get('bleed', 0)
    if new_bleed > 0:
        await set_bleed(user_id, new_bleed)
    
    enemy_hp -= player_damage
    if enemy_hp < 0:
        enemy_hp = 0
    
    await update_dungeon_hp(user_id, current_hp, enemy_hp)
    
    if enemy_hp <= 0:
        await clear_bleed(user_id)
        await dungeon_stage_win(update, context, dungeon_type)
        return
    
    # ===== نوبت دشمن =====
    enemy_damage = enemy_atk - total_def
    if enemy_damage < 1:
        enemy_damage = 1
    
    current_hp -= enemy_damage
    if current_hp < 0:
        current_hp = 0
    
    await update_dungeon_hp(user_id, current_hp, enemy_hp)
    await update_user_hp(user_id, current_hp)
    
    if current_hp <= 0:
        await player_died(user_id)
        await query.edit_message_text(
            f"💀 **تو در نبرد با {dungeon_data['name']} به شهادت رسیدی!**\n\n"
            f"⏱️ تا ۱ ساعت دیگه ری‌اسپان میشی.\n"
            f"بعد از ری‌اسپان، جون تو نصف میشه.",
            parse_mode="Markdown"
        )
        return
    
    # ===== ساخت پیام نتیجه =====
    msg = (
        f"⚔️ **ادامه نبرد با {dungeon_data['name']}**\n\n"
        f"🛡️ **تجهیزات تو:**\n"
        f"🗡️ سلاح: {weapon_name} (+{atk_bonus} اتک)\n"
        f"🛡️ زره: {armor_name} (+{def_bonus} دفاع)\n\n"
        f"💥 **تو به {dungeon_data['name']} حمله کردی!**\n"
        f"   🔹 اتک تو: {total_atk} | دفاع دشمن: {enemy_def}\n"
        f"   🔹 دمیج پایه: {player_damage}\n"
    )
    
    if bonus_messages:
        for bonus_msg in bonus_messages:
            msg += f"   ✨ {bonus_msg}\n"
    
    msg += (
        f"   🔹 دمیج نهایی: {total_damage_dealt}\n"
        f"   🔹 جون باقی‌مونده دشمن: {enemy_hp}\n\n"
        f"⚔️ **{dungeon_data['name']} بهت حمله کرد!**\n"
        f"   🔹 اتک دشمن: {enemy_atk} | دفاع تو: {total_def}\n"
        f"   🔹 دمیج خورده: {enemy_damage}\n"
        f"   🔹 جون باقی‌مونده تو: {current_hp}"
    )
    
    keyboard = [[InlineKeyboardButton("⚔️ ادامه", callback_data=f"dungeon_continue_{dungeon_type}", style="primary")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==========================================
# پیروزی مرحله
# ==========================================
async def dungeon_stage_win(update: Update, context: ContextTypes.DEFAULT_TYPE, dungeon_type: str):
    """پیروزی در یک مرحله از دانجن"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    user_id = query.from_user.id
    
    dungeon = await get_dungeon(user_id)
    if not dungeon:
        await query.edit_message_text("❌ دانجن فعالی وجود ندارد!")
        return
    
    dungeon_data = DUNGEONS.get(dungeon_type)
    stage = dungeon['stage']
    total_stages = dungeon_data['stages']
    
    if stage >= total_stages:
        await dungeon_final_win(update, context, dungeon_type)
        return
    
    new_stage = stage + 1
    await update_dungeon_stage(user_id, new_stage)
    await update_dungeon_hp(user_id, dungeon['current_hp'], dungeon_data['enemy_hp'])
    
    # ===== آپدیت پیشرفت کوئست =====
    if dungeon_type == "goblin":
        await update_quest_progress(user_id, "kill_goblin")
    elif dungeon_type == "troll":
        await update_quest_progress(user_id, "kill_troll")
    
    # ===== پاک کردن خونریزی بعد از هر مرحله =====
    await clear_bleed(user_id)
    
    # ===== سیستم دراپ آیتم =====
    drop_chance = random.random()
    drop_item = None
    for item in dungeon_data['drop_items']:
        if drop_chance <= item['chance']:
            drop_item = item
            break
    
    msg = f"🎉 **پیروزی در مرحله {stage}!**\n\n"
    msg += f"✅ مرحله {stage} رو با موفقیت به اتمام رسوندی!\n"
    msg += f"📍 مرحله بعدی در انتظارته...\n\n"
    
    if drop_item:
        await add_item_to_inventory(user_id, drop_item['name'], drop_item['type'])
        msg += f"🎁 **دراپ آیتم:**\n"
        msg += f"   ✨ {drop_item['name']} به اینونتوری اضافه شد!\n\n"
    else:
        msg += f"😔 متاسفانه هیچ آیتمی از دشمنان نیفتاد!\n\n"
    
    keyboard = [[InlineKeyboardButton("⚔️ مرحله بعد", callback_data=f"dungeon_next_stage_{dungeon_type}", style="success")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==========================================
# پیروزی نهایی
# ==========================================
async def dungeon_final_win(update: Update, context: ContextTypes.DEFAULT_TYPE, dungeon_type: str):
    """پیروزی نهایی در دانجن و دریافت پاداش"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    user_id = query.from_user.id
    dungeon_data = DUNGEONS.get(dungeon_type)
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    base_gold = dungeon_data['base_reward_gold']
    base_upgrade = dungeon_data['base_reward_upgrade']
    base_exp = dungeon_data['base_reward_exp']
    
    lck_bonus = 1 + (player.stats.lck * 0.015)
    final_gold = int(base_gold * lck_bonus)
    
    conn = await get_db()
    await conn.execute(
        "UPDATE users SET gold = gold + $1, upgrade_points = upgrade_points + $2 WHERE user_id = $3",
        final_gold, base_upgrade, user_id
    )
    await conn.close()
    
    # ===== پاک کردن خونریزی =====
    await clear_bleed(user_id)
    
    result = await add_exp(user_id, base_exp)
    
    await clear_panel_owner(update, context)
    await end_dungeon(user_id)
    
    msg = (
        f"🏆 **پیروزی نهایی!**\n\n"
        f"✅ {dungeon_data['name']} رو با موفقیت به اتمام رسوندی!\n\n"
        f"🎁 **پاداش‌ها:**\n"
        f"💰 {final_gold} سکه (با اعمال شانس)\n"
        f"⭐ {base_upgrade} آپگرید پوینت\n"
        f"✨ {base_exp} تجربه\n"
    )
    
    if result and result['leveled_up']:
        msg += f"\n🎉 **لول آپ!**\n"
        msg += f"⭐ لول جدید: {result['new_level']}\n"
        msg += f"📈 اکس‌پی باقی‌مونده: {result['new_exp']} / {result['new_max_exp']}"
    
    await query.edit_message_text(msg, parse_mode="Markdown")

# ==========================================
# ادامه نبرد
# ==========================================
async def dungeon_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ادامه نبرد بعد از حمله"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    dungeon_type = query.data.replace("dungeon_continue_", "")
    await dungeon_battle_round(update, context, dungeon_type)

# ==========================================
# مرحله بعد
# ==========================================
async def dungeon_next_stage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفتن به مرحله بعد از دانجن"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    dungeon_type = query.data.replace("dungeon_next_stage_", "")
    await dungeon_battle_round(update, context, dungeon_type)

# ==========================================
# فرار از دانجن
# ==========================================
async def dungeon_flee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فرار از دانجن"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    user_id = query.from_user.id
    
    await end_dungeon(user_id)
    await clear_bleed(user_id)
    await clear_panel_owner(update, context)
    
    await query.edit_message_text(
        "🏃 **تو از دانجن فرار کردی!**\n\n"
        "امیدوارم دفعه بعد شجاع‌تر باشی!",
        parse_mode="Markdown"
    )

# ==========================================
# منوی پوشن
# ==========================================
async def dungeon_potion_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی پوشن‌ها برای استفاده در نبرد"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    user_id = query.from_user.id
    
    items = await get_inventory(user_id)
    potions = []
    for item in items:
        if item['item_type'] == 'consumable' and item['quantity'] > 0:
            potions.append(Item(
                id=item['id'],
                user_id=item['user_id'],
                item_type=item['item_type'],
                item_name=item['item_name'],
                quantity=item['quantity'],
                level=item['level'],
                equipped=item['equipped']
            ))
    
    if not potions:
        await query.edit_message_text(
            "❌ **هیچ پوشنی نداری!**\n\n"
            "از شاپ می‌تونی پوشن بخری.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به نبرد", callback_data="dungeon_back_to_battle", style="primary")]
            ]),
            parse_mode="Markdown"
        )
        return
    
    msg = "🧪 **پوشن‌های موجود:**\n\n"
    keyboard = []
    
    for potion in potions:
        msg += f"• {potion.get_display_name()} ×{potion.quantity}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"استفاده {potion.get_display_name()}",
                callback_data=f"dungeon_use_potion_{potion.item_name}_{potion.level}",
                style="success"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت به نبرد", callback_data="dungeon_back_to_battle", style="primary")
    ])
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==========================================
# استفاده از پوشن در نبرد
# ==========================================
async def dungeon_use_potion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استفاده از پوشن در نبرد"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    data = query.data
    parts = data.replace("dungeon_use_potion_", "").split("_")
    if len(parts) >= 2:
        level = int(parts[-1])
        item_name = "_".join(parts[:-1])
    else:
        await query.edit_message_text("❌ خطا در شناسایی پوشن!")
        return
    
    user_id = query.from_user.id
    
    dungeon = await get_dungeon(user_id)
    if not dungeon:
        await query.edit_message_text("❌ دانجن فعالی وجود ندارد!")
        return
    
    dungeon_type = dungeon['dungeon_type']
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    item_stats = ITEM_STATS.get('consumable', {}).get(item_name, {})
    heal_percent = item_stats.get('heal_percent', 0)
    
    if heal_percent == 0:
        await query.edit_message_text("❌ این آیتم قابلیت درمان ندارد!")
        return
    
    heal_amount = int(player.stats.max_hp * heal_percent)
    new_hp = min(player.stats.hp + heal_amount, player.stats.max_hp)
    
    used_item = await use_consumable(user_id, item_name, level)
    
    if not used_item:
        await query.edit_message_text("❌ این پوشن موجود نیست!")
        return
    
    await update_user_hp(user_id, new_hp)
    await update_dungeon_hp(user_id, new_hp, dungeon['enemy_hp'])
    
    await query.edit_message_text(
        f"✅ **از {item_name} استفاده شد!**\n\n"
        f"❤️ {heal_amount} جون بهت اضافه شد!\n"
        f"❤️ **جون جدید**: {new_hp} / {player.stats.max_hp}\n"
        f"`{create_bar(new_hp, player.stats.max_hp)}`\n\n"
        f"برای ادامه به نبرد برگرد:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ برگشت به نبرد", callback_data="dungeon_back_to_battle", style="primary")]
        ]),
        parse_mode="Markdown"
    )

# ==========================================
# برگشت به نبرد
# ==========================================
async def dungeon_back_to_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برگشت به صفحه نبرد"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    await set_panel_owner(update, context)
    
    user_id = query.from_user.id
    dungeon = await get_dungeon(user_id)
    
    if not dungeon:
        await query.edit_message_text("❌ دانجن فعالی وجود ندارد!")
        return
    
    dungeon_type = dungeon['dungeon_type']
    await dungeon_battle_round(update, context, dungeon_type)

# ==========================================
# برگشت به پنل اصلی
# ==========================================
async def dungeon_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برگشت به پنل اصلی دانجن‌ها"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    
    user_id = query.from_user.id
    
    await clear_panel_owner(update, context)
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await query.edit_message_text("❌ شما ثبت‌نام نکردید!")
        return
    
    if await check_active_dungeon(user_id):
        await query.edit_message_text(
            "⚠️ **شما در حال حاضر یک دانجن فعال دارید!**\n"
            "قبل از شروع ماموریت جدید، ماموریت فعلی رو تموم کن.",
            parse_mode="Markdown"
        )
        return
    
    if await is_player_dead(user_id):
        respawn_time = await get_respawn_time(user_id)
        minutes = respawn_time // 60
        seconds = respawn_time % 60
        await query.edit_message_text(
            f"💀 **شما در نبرد به شهادت رسیدی!**\n\n"
            f"⏱️ زمان تا ری‌اسپان: {minutes}:{seconds:02d}",
            parse_mode="Markdown"
        )
        return
    
    msg = (
        "🏰 **سالن ماموریت‌های شوالیه‌ها**\n\n"
        "به سالن ماموریت‌ها خوش آمدی، شوالیه! \n"
        "شهروندان برای نجات سرزمین‌شان از دست هیولاها به کمک نیاز دارند.\n"
        "هر ماموریت پاداش‌های مخصوص خودش رو داره.\n\n"
        "📋 **ماموریت‌های موجود:**\n"
    )
    
    keyboard = []
    
    for key, dungeon_data in DUNGEONS.items():
        cooldown = await get_cooldown_remaining(user_id, key)
        level_required = dungeon_data.get('level_required', 0)
        can_access = player.stats.level >= level_required
        
        status = ""
        if cooldown > 0:
            minutes = cooldown // 60
            seconds = cooldown % 60
            status = f" ⏱️ {minutes}:{seconds:02d}"
        elif not can_access:
            status = f" 🔒 نیاز: لول {level_required}"
        
        btn_text = f"{dungeon_data['emoji']} {dungeon_data['name']}{status}"
        
        if not can_access:
            callback = "dungeon_level_locked"
        elif cooldown > 0:
            callback = "dungeon_locked"
        else:
            callback = f"dungeon_start_{key}"
        
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback, style="primary")])
    
    keyboard.append([InlineKeyboardButton("🔙 بستن پنل", callback_data="dungeon_close", style="danger")])
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==========================================
# بستن پنل دانجن
# ==========================================
async def dungeon_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن پنل دانجن"""
    query = update.callback_query
    await query.answer()
    
    if not await check_ownership(update, context):
        return
    
    user_id = query.from_user.id
    
    await clear_panel_owner(update, context)
    await query.delete_message()

# ==========================================
# دکمه‌های قفل شده
# ==========================================
async def dungeon_locked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام برای دانجن قفل شده"""
    query = update.callback_query
    await query.answer("⛔ این ماموریت در حال حاضر در دسترس نیست!", show_alert=True)

async def dungeon_level_locked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام برای دانجن قفل شده به خاطر لول"""
    query = update.callback_query
    await query.answer("🔒 لول شما برای این ماموریت کافی نیست!", show_alert=True)

