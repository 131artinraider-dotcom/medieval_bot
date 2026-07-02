import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_user, get_db, get_equipped, get_active_fight,
    create_fight, get_fight, update_fight, end_fight,
    set_fight_shield, has_fight_shield, get_shield_remaining,
    get_upgrade_points, remove_upgrade_points, add_upgrade_points,
    add_exp, update_user_hp, use_consumable,
    get_inventory, create_fight_tables
)
from models import Player, Item
from config import (
    CLASS_STAMINA, WEAPON_STAMINA, DUNGEONS, ITEM_STATS,
    FIGHT_GOLD_RATIO, FIGHT_UPGRADE_RATIO,
    FIGHT_SHIELD_MINUTES, FIGHT_MAX_POTIONS, get_weapon_category
)
from handlers.panel_utils import register_panel, check_panel_ownership


def create_bar(current, max_val, length=12):
    if max_val <= 0:
        return "░" * length
    filled = int((current / max_val) * length)
    filled = min(filled, length)
    return "█" * filled + "░" * (length - filled)


def get_stamina_costs(weapon_name: str) -> dict:
    cat = get_weapon_category(weapon_name)
    return WEAPON_STAMINA.get(cat, WEAPON_STAMINA["sword"])


async def get_player_weapon_info(user_id: int):
    """سلاح equipped پلیر + bonus"""
    equipped = await get_equipped(user_id)
    weapon = None
    weapon_atk = 0
    weapon_name = "بدون سلاح"
    for item in equipped:
        if item.item_type == "weapon":
            weapon = item
            weapon_name = item.item_name
            stats = ITEM_STATS.get("weapon", {}).get(item.item_name, {})
            weapon_atk = stats.get("atk_bonus", 0)
            break
    return weapon_name, weapon_atk


async def get_player_armor_info(user_id: int):
    """زره equipped پلیر + bonus"""
    equipped = await get_equipped(user_id)
    armor_def = 0
    for item in equipped:
        if item.item_type == "armor":
            stats = ITEM_STATS.get("armor", {}).get(item.item_name, {})
            armor_def = stats.get("def_bonus", 0)
            break
    return armor_def


def calc_damage(attacker_atk: int, weapon_atk: int, defender_def: int,
                armor_def: int, move: str, weapon_name: str, attacker_lck: int) -> tuple:
    """محاسبه دمیج + پیام بونس"""
    base_atk = attacker_atk + weapon_atk
    total_def = defender_def + armor_def

    # ضریب حمله
    if move == "heavy":
        multiplier = 2.0
    else:
        multiplier = 1.0

    raw_damage = max(0, base_atk * multiplier - total_def * 0.5)

    # شانس کریت (LCK)
    crit_chance = 0.05 + attacker_lck * 0.005
    bonus_msgs = []
    if random.random() < crit_chance:
        raw_damage *= 1.5
        bonus_msgs.append("💥 ضربه کریتیکال!")

    # بونس سلاح
    cat = get_weapon_category(weapon_name)
    from config import WEAPON_BONUSES
    weapon_bonus = WEAPON_BONUSES.get(cat, {})
    if weapon_bonus:
        chance_dict = weapon_bonus.get("chances", {})
        bonus_chance = chance_dict.get(weapon_name, weapon_bonus.get("chance", 0))
        if random.random() < bonus_chance:
            bonus_type = weapon_bonus.get("type")
            if bonus_type == "deep_wound":
                raw_damage *= 1.3
                bonus_msgs.append("⚔️ زخم عمیق!")
            elif bonus_type == "execute":
                raw_damage *= 1.4
                bonus_msgs.append("🗡️ ضربه مرگبار!")
            elif bonus_type == "critical":
                raw_damage *= 1.5
                bonus_msgs.append("🔪 کریتیکال خنجر!")
            elif bonus_type == "armor_pierce":
                raw_damage += total_def * 0.4
                bonus_msgs.append("🪓 دفاع نادیده گرفته شد!")

    return int(raw_damage), bonus_msgs


def calc_defense_reduction(defender_def: int, armor_def: int) -> float:
    """چقدر دمیج با دفاع کاهش پیدا میکنه"""
    total_def = defender_def + armor_def
    return min(0.75, total_def * 0.003)


def check_extra_turn(spd: int) -> int:
    """تعداد نوبت اضافه بر اساس سرعت - برمیگردونه ۰، ۱ یا ۲"""
    extra_chance = min(0.6, spd * 0.015)
    if random.random() < extra_chance:
        double_chance = min(0.3, spd * 0.008)
        if random.random() < double_chance:
            return 2
        return 1
    return 0


def build_fight_panel(fight, a_name: str, d_name: str,
                      a_max_hp: int, d_max_hp: int,
                      a_max_stam: int, d_max_stam: int,
                      is_pvp: bool = True) -> str:
    a_hp = fight["attacker_hp"]
    d_hp = fight["defender_hp"]
    a_stam = fight["attacker_stamina"]
    d_stam = fight["defender_stamina"]
    a_pot = fight["attacker_potions"]
    d_pot = fight["defender_potions"]
    current = fight["current_turn"]
    att_id = fight["attacker_id"]

    turn_name = a_name if current == att_id else d_name

    msg = (
        f"⚔️ **نبرد**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴 **{a_name}**\n"
        f"❤️ {a_hp}/{a_max_hp} `{create_bar(a_hp, a_max_hp)}`\n"
        f"⚡ {a_stam}/{a_max_stam} `{create_bar(a_stam, a_max_stam)}`\n"
        f"🧪 پوشن: {a_pot}/{FIGHT_MAX_POTIONS}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔵 **{d_name}**\n"
        f"❤️ {d_hp}/{d_max_hp} `{create_bar(d_hp, d_max_hp)}`\n"
    )
    if is_pvp:
        msg += (
            f"⚡ {d_stam}/{d_max_stam} `{create_bar(d_stam, d_max_stam)}`\n"
            f"🧪 پوشن: {d_pot}/{FIGHT_MAX_POTIONS}\n"
        )
    msg += (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 نوبت: **{turn_name}**"
    )
    return msg


def build_fight_keyboard(fight_id: int, user_id: int, fight,
                         stam_costs: dict, has_double: bool,
                         current_stam: int, is_pvp: bool = True) -> InlineKeyboardMarkup:
    """دکمه‌های نبرد برای کاربر جاری"""
    can_light = current_stam >= stam_costs["light"]
    can_heavy = current_stam >= stam_costs["heavy"]
    can_defend = current_stam >= stam_costs["defend"]

    rows = []

    if has_double and can_light:
        rows.append([
            InlineKeyboardButton(
                f"🔪×2 دو ضربه سبک ({stam_costs['light']*2}⚡)",
                callback_data=f"fight_double_{fight_id}", style="success"
            )
        ])
        rows.append([
            InlineKeyboardButton(
                f"⚔️ سبک ({stam_costs['light']}⚡)" if can_light else f"⚔️ سبک (کم⚡)",
                callback_data=f"fight_light_{fight_id}",
                style="primary" if can_light else "danger"
            ),
            InlineKeyboardButton(
                f"💥 سنگین ({stam_costs['heavy']}⚡)" if can_heavy else f"💥 سنگین (کم⚡)",
                callback_data=f"fight_heavy_{fight_id}",
                style="primary" if can_heavy else "danger"
            ),
        ])
    else:
        rows.append([
            InlineKeyboardButton(
                f"⚔️ سبک ({stam_costs['light']}⚡)" if can_light else f"⚔️ سبک (کم⚡)",
                callback_data=f"fight_light_{fight_id}",
                style="primary" if can_light else "danger"
            ),
            InlineKeyboardButton(
                f"💥 سنگین ({stam_costs['heavy']}⚡)" if can_heavy else f"💥 سنگین (کم⚡)",
                callback_data=f"fight_heavy_{fight_id}",
                style="primary" if can_heavy else "danger"
            ),
        ])

    rows.append([
        InlineKeyboardButton(
            f"🛡️ دفاع ({stam_costs['defend']}⚡)" if can_defend else f"🛡️ دفاع (کم⚡)",
            callback_data=f"fight_defend_{fight_id}",
            style="primary" if can_defend else "danger"
        ),
        InlineKeyboardButton(
            f"🧪 پوشن",
            callback_data=f"fight_potion_{fight_id}",
            style="success"
        ),
    ])

    if current_stam < min(stam_costs["light"], stam_costs["defend"]):
        rows.append([
            InlineKeyboardButton(
                "⏭️ اسکیپ (استامینا نداری)",
                callback_data=f"fight_skip_{fight_id}",
                style="danger"
            )
        ])

    return InlineKeyboardMarkup(rows)


# ==========================================
# شروع فایت
# ==========================================
async def fight_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کامند /fight یا فایت"""
    await create_fight_tables()

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # چک فایت فعال
    active = await get_active_fight(user_id)
    if active:
        await update.message.reply_text(
            "⚠️ **تو الان یه فایت فعال داری!**\n"
            "اول اونو تموم کن.",
            parse_mode="Markdown"
        )
        return

    # پیدا کردن هدف (منشن یا ریپلای)
    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        mention = context.args[0].replace("@", "")
        # سرچ توی اعضای گروه
        try:
            members = await context.bot.get_chat_member(chat_id, f"@{mention}")
            target_user = members.user
        except Exception:
            await update.message.reply_text("❌ کاربر پیدا نشد! به پیامش ریپلای کن یا منشنش کن.")
            return
    else:
        await update.message.reply_text(
            "❌ باید هدف رو مشخص کنی!\n"
            "روش: `/fight @username` یا ریپلای به پیام کاربر",
            parse_mode="Markdown"
        )
        return

    if target_user.id == user_id:
        await update.message.reply_text("❌ نمیتونی با خودت فایت کنی!")
        return

    if target_user.is_bot:
        await update.message.reply_text("❌ نمیتونی با بات فایت کنی!")
        return

    # بررسی ثبت‌نام طرفین
    attacker_row = await get_user(user_id)
    attacker = Player.from_db_row(attacker_row)
    if not attacker or not attacker.is_registered:
        await update.message.reply_text("❌ اول باید ثبت‌نام کنی! /start")
        return

    defender_row = await get_user(target_user.id)
    defender = Player.from_db_row(defender_row)
    if not defender or not defender.is_registered:
        await update.message.reply_text("❌ این کاربر هنوز بازی رو شروع نکرده!")
        return

    # چک فایت فعال حریف
    defender_active = await get_active_fight(target_user.id)
    if defender_active:
        await update.message.reply_text(
            f"⚠️ **{defender.character_name}** الان توی یه فایت دیگه‌ست!\n"
            "بعداً امتحان کن.",
            parse_mode="Markdown"
        )
        return

    # چک اختلاف لول
    level_diff = abs(attacker.stats.level - defender.stats.level)
    if level_diff > 5:
        await update.message.reply_text(
            f"❌ اختلاف لول خیلی زیاده! ({level_diff} لول)\n"
            "حداکثر اختلاف مجاز: ۵ لول",
            parse_mode="Markdown"
        )
        return

    # شیلد حریف
    if await has_fight_shield(target_user.id):
        remaining = await get_shield_remaining(target_user.id)
        await update.message.reply_text(
            f"🛡️ **{defender.character_name}** الان شیلد داره!\n"
            f"⏳ {remaining} دقیقه دیگه شیلدش تموم میشه.",
            parse_mode="Markdown"
        )
        return

    # ذخیره اطلاعات درخواست فایت
    context.bot_data[f"fight_req_{user_id}_{target_user.id}"] = {
        "attacker_id": user_id,
        "attacker_name": attacker.character_name,
        "defender_id": target_user.id,
        "defender_name": defender.character_name,
        "chat_id": chat_id,
        "ts": __import__("time").time()
    }

    keyboard = [
        [
            InlineKeyboardButton("✅ قبوله، بزن بریم!", callback_data=f"fight_accept_{user_id}", style="success"),
            InlineKeyboardButton("❌ رد میکنم", callback_data=f"fight_decline_{user_id}", style="danger"),
        ]
    ]

    msg = await update.message.reply_text(
        f"⚔️ **درخواست فایت!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴 {attacker.character_name} (Lv.{attacker.stats.level})\n"
        f"   ❤️ {attacker.stats.hp} | ⚔️ {attacker.stats.atk} | 🛡️ {attacker.stats.defense}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔵 {defender.character_name} (Lv.{defender.stats.level})\n"
        f"   ❤️ {defender.stats.hp} | ⚔️ {defender.stats.atk} | 🛡️ {defender.stats.defense}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ {defender.character_name} ۵ دقیقه وقت داره قبول کنه\n"
        f"اگه رد کنه، فایت زوری شروع میشه!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    register_panel(msg.message_id, user_id, context, chat_id)

    # تایمر ۵ دقیقه برای auto-decline
    context.job_queue.run_once(
        auto_start_forced_fight,
        when=300,
        data={"attacker_id": user_id, "defender_id": target_user.id,
              "message_id": msg.message_id, "chat_id": chat_id},
        name=f"fight_timeout_{user_id}_{target_user.id}"
    )


async def auto_start_forced_fight(context):
    """بعد از ۵ دقیقه اگه قبول نکرد، فایت زوری شروع میشه"""
    data = context.job.data
    attacker_id = data["attacker_id"]
    defender_id = data["defender_id"]
    chat_id = data["chat_id"]
    message_id = data["message_id"]

    req_key = f"fight_req_{attacker_id}_{defender_id}"
    if req_key not in context.bot_data:
        return  # قبلاً handle شده

    context.bot_data.pop(req_key, None)

    try:
        await context.bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=message_id, reply_markup=None
        )
    except Exception:
        pass

    await _start_forced_fight(context, attacker_id, defender_id, chat_id)


async def fight_accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قبول تن به تن"""
    query = update.callback_query
    user_id = query.from_user.id
    attacker_id = int(query.data.replace("fight_accept_", ""))

    req_key = f"fight_req_{attacker_id}_{user_id}"
    req = context.bot_data.get(req_key)

    if not req:
        await query.answer("❌ این درخواست منقضی شده!", show_alert=True)
        return

    if user_id != req["defender_id"]:
        await query.answer("❌ این درخواست برای تو نیست!", show_alert=True)
        return

    # لغو تایمر
    jobs = context.job_queue.get_jobs_by_name(f"fight_timeout_{attacker_id}_{user_id}")
    for job in jobs:
        job.schedule_removal()

    context.bot_data.pop(req_key, None)
    await _start_pvp_fight(update, context, attacker_id, user_id, req["chat_id"])


async def fight_decline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد کردن — فایت زوری"""
    query = update.callback_query
    user_id = query.from_user.id
    attacker_id = int(query.data.replace("fight_decline_", ""))

    req_key = f"fight_req_{attacker_id}_{user_id}"
    req = context.bot_data.get(req_key)

    if not req:
        await query.answer("❌ این درخواست منقضی شده!", show_alert=True)
        return

    if user_id != req["defender_id"]:
        await query.answer("❌ این درخواست برای تو نیست!", show_alert=True)
        return

    # لغو تایمر
    jobs = context.job_queue.get_jobs_by_name(f"fight_timeout_{attacker_id}_{user_id}")
    for job in jobs:
        job.schedule_removal()

    context.bot_data.pop(req_key, None)

    try:
        await query.message.delete()
    except Exception:
        pass

    await _start_forced_fight(context, attacker_id, user_id, req["chat_id"])


async def _start_pvp_fight(update, context, attacker_id: int, defender_id: int, chat_id: int):
    """شروع فایت تن به تن"""
    query = update.callback_query

    attacker_row = await get_user(attacker_id)
    defender_row = await get_user(defender_id)
    attacker = Player.from_db_row(attacker_row)
    defender = Player.from_db_row(defender_row)

    a_stam = CLASS_STAMINA.get(attacker.class_key, 100)
    d_stam = CLASS_STAMINA.get(defender.class_key, 100)

    fight_id = await create_fight(
        attacker_id, defender_id, "pvp", chat_id,
        attacker.stats.hp, defender.stats.hp, a_stam, d_stam
    )

    fight = await get_fight(fight_id)
    a_weapon, _ = await get_player_weapon_info(attacker_id)
    d_weapon, _ = await get_player_weapon_info(defender_id)

    msg_text = build_fight_panel(
        fight, attacker.character_name, defender.character_name,
        attacker.stats.max_hp, defender.stats.max_hp, a_stam, d_stam, True
    )

    stam_costs = get_stamina_costs(a_weapon)
    has_double = get_weapon_category(a_weapon) == "dagger"
    keyboard = build_fight_keyboard(fight_id, attacker_id, fight, stam_costs, has_double, a_stam, True)

    try:
        await query.edit_message_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")
        msg_id = query.message.message_id
    except Exception:
        sent = await context.bot.send_message(chat_id, msg_text, reply_markup=keyboard, parse_mode="Markdown")
        msg_id = sent.message_id

    await update_fight(fight_id, message_id=msg_id, status="active")
    register_panel(msg_id, attacker_id, context, chat_id, panel_type="fight")
    context.bot_data[f"fight_panel_{fight_id}"] = {
        "attacker_id": attacker_id, "defender_id": defender_id,
        "a_max_hp": attacker.stats.max_hp, "d_max_hp": defender.stats.max_hp,
        "a_max_stam": a_stam, "d_max_stam": d_stam,
        "a_name": attacker.character_name, "d_name": defender.character_name,
        "fight_type": "pvp"
    }


async def _start_forced_fight(context, attacker_id: int, defender_id: int, chat_id: int):
    """فایت زوری — بات بجای defender بازی میکنه"""
    attacker_row = await get_user(attacker_id)
    defender_row = await get_user(defender_id)
    attacker = Player.from_db_row(attacker_row)
    defender = Player.from_db_row(defender_row)

    a_stam = CLASS_STAMINA.get(attacker.class_key, 100)
    d_stam = CLASS_STAMINA.get(defender.class_key, 100)

    fight_id = await create_fight(
        attacker_id, defender_id, "forced", chat_id,
        attacker.stats.hp, defender.stats.hp, a_stam, d_stam
    )

    a_weapon, a_watk = await get_player_weapon_info(attacker_id)
    a_armor_def = await get_player_armor_info(attacker_id)
    d_weapon, d_watk = await get_player_weapon_info(defender_id)
    d_armor_def = await get_player_armor_info(defender_id)

    # شبیه‌سازی نبرد زوری
    a_hp = attacker.stats.hp
    d_hp = defender.stats.hp
    round_num = 0
    log = []

    while a_hp > 0 and d_hp > 0 and round_num < 30:
        round_num += 1

        # حمله attacker
        dmg, _ = calc_damage(attacker.stats.atk, a_watk, defender.stats.defense, d_armor_def,
                              "light", a_weapon, attacker.stats.lck)
        d_hp = max(0, d_hp - dmg)
        log.append(f"🔴 {attacker.character_name}: -{dmg} → {defender.character_name}")
        if d_hp <= 0:
            break

        # حمله defender (بات ساده)
        dmg2, _ = calc_damage(defender.stats.atk, d_watk, attacker.stats.defense, a_armor_def,
                               "light", d_weapon, defender.stats.lck)
        a_hp = max(0, a_hp - dmg2)
        log.append(f"🔵 {defender.character_name}: -{dmg2} → {attacker.character_name}")

    winner_id = attacker_id if d_hp <= 0 else defender_id
    loser_id = defender_id if winner_id == attacker_id else attacker_id

    await end_fight(fight_id, "finished")
    await _give_rewards(context, winner_id, loser_id, attacker, defender, "forced", chat_id, log)


# ==========================================
# پردازش حرکات
# ==========================================
async def fight_move_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش حمله سبک، سنگین، دفاع، دوتایی، اسکیپ"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data  # fight_light_123 / fight_heavy_123 / fight_defend_123 ...

    parts = data.split("_")
    move = parts[1]  # light / heavy / defend / double / skip / potion
    fight_id = int(parts[2])

    fight = await get_fight(fight_id)
    if not fight or fight["status"] != "active":
        await query.answer("❌ این فایت دیگه فعال نیست!", show_alert=True)
        return

    is_pvp = fight["fight_type"] == "pvp"
    attacker_id = fight["attacker_id"]
    defender_id = fight["defender_id"]

    # بررسی نوبت
    if fight["current_turn"] != user_id:
        await query.answer("❌ نوبت تو نیست!", show_alert=True)
        return

    # بررسی اینکه user جزء بازیکنان باشه
    if user_id not in (attacker_id, defender_id):
        await query.answer("❌ تو توی این فایت نیستی!", show_alert=True)
        return

    panel_data = context.bot_data.get(f"fight_panel_{fight_id}", {})
    a_name = panel_data.get("a_name", "بازیکن ۱")
    d_name = panel_data.get("d_name", "بازیکن ۲")
    a_max_hp = panel_data.get("a_max_hp", 1000)
    d_max_hp = panel_data.get("d_max_hp", 1000)
    a_max_stam = panel_data.get("a_max_stam", 100)
    d_max_stam = panel_data.get("d_max_stam", 100)

    is_attacker = (user_id == attacker_id)
    opponent_id = defender_id if is_attacker else attacker_id

    attacker_row = await get_user(attacker_id)
    defender_row = await get_user(defender_id)
    attacker = Player.from_db_row(attacker_row)
    defender = Player.from_db_row(defender_row)

    my_player = attacker if is_attacker else defender
    opp_player = defender if is_attacker else attacker

    my_weapon, my_watk = await get_player_weapon_info(user_id)
    opp_armor_def = await get_player_armor_info(opponent_id)
    my_armor_def = await get_player_armor_info(user_id)

    stam_costs = get_stamina_costs(my_weapon)
    has_double = get_weapon_category(my_weapon) == "dagger"

    cur_a_hp = fight["attacker_hp"]
    cur_d_hp = fight["defender_hp"]
    cur_a_stam = fight["attacker_stamina"]
    cur_d_stam = fight["defender_stamina"]

    my_hp = cur_a_hp if is_attacker else cur_d_hp
    opp_hp = cur_d_hp if is_attacker else cur_a_hp
    my_stam = cur_a_stam if is_attacker else cur_d_stam
    my_pot = fight["attacker_potions"] if is_attacker else fight["defender_potions"]

    result_msgs = []
    fight_ended = False
    winner_id = None

    if move == "potion":
        await query.answer()
        await _show_fight_potion_menu(query, context, fight_id, user_id)
        return

    elif move == "skip":
        await query.answer("⏭️ اسکیپ کردی")
        result_msgs.append(f"⏭️ {'تو' if is_attacker else d_name} استامینا نداشت و اسکیپ کرد!")

    elif move == "defend":
        cost = stam_costs["defend"]
        if my_stam < cost:
            await query.answer("❌ استامینا کافی نداری!", show_alert=True)
            return
        my_stam -= cost
        result_msgs.append(f"🛡️ دفاع کردی! (حمله بعدی کاهش میابه)")
        context.bot_data[f"fight_defending_{fight_id}_{user_id}"] = True

    elif move in ("light", "heavy", "double"):
        defending = context.bot_data.pop(f"fight_defending_{fight_id}_{opponent_id}", False)

        if move == "light":
            cost = stam_costs["light"]
            if my_stam < cost:
                await query.answer("❌ استامینا کافی نداری!", show_alert=True)
                return
            my_stam -= cost
            dmg, bonus = calc_damage(my_player.stats.atk, my_watk, opp_player.stats.defense,
                                     opp_armor_def, "light", my_weapon, my_player.stats.lck)
            if defending:
                red = calc_defense_reduction(opp_player.stats.defense, opp_armor_def)
                dmg = int(dmg * (1 - red))
                result_msgs.append(f"🛡️ {d_name if is_attacker else a_name} دفاع کرد! دمیج کاهش یافت")
            opp_hp = max(0, opp_hp - dmg)
            result_msgs.append(f"⚔️ حمله سبک: **{dmg}** دمیج")
            result_msgs.extend(bonus)

        elif move == "heavy":
            cost = stam_costs["heavy"]
            if my_stam < cost:
                await query.answer("❌ استامینا کافی نداری!", show_alert=True)
                return
            my_stam -= cost
            dmg, bonus = calc_damage(my_player.stats.atk, my_watk, opp_player.stats.defense,
                                     opp_armor_def, "heavy", my_weapon, my_player.stats.lck)
            if defending:
                red = calc_defense_reduction(opp_player.stats.defense, opp_armor_def)
                dmg = int(dmg * (1 - red))
                result_msgs.append(f"🛡️ {d_name if is_attacker else a_name} دفاع کرد! دمیج کاهش یافت")
            opp_hp = max(0, opp_hp - dmg)
            result_msgs.append(f"💥 حمله سنگین: **{dmg}** دمیج")
            result_msgs.extend(bonus)

        elif move == "double" and has_double:
            cost = stam_costs["light"] * 2
            if my_stam < cost:
                await query.answer("❌ استامینا کافی نداری!", show_alert=True)
                return
            my_stam -= cost
            total_dmg = 0
            for i in range(2):
                dmg, bonus = calc_damage(my_player.stats.atk, my_watk, opp_player.stats.defense,
                                         opp_armor_def, "light", my_weapon, my_player.stats.lck)
                total_dmg += dmg
                result_msgs.extend(bonus)
            if defending:
                red = calc_defense_reduction(opp_player.stats.defense, opp_armor_def)
                total_dmg = int(total_dmg * (1 - red))
            opp_hp = max(0, opp_hp - total_dmg)
            result_msgs.append(f"🔪×2 دو ضربه سبک: **{total_dmg}** دمیج")

        # بررسی پایان
        if opp_hp <= 0:
            fight_ended = True
            winner_id = user_id

    # بروزرسانی استامینا (بعد از هر نوبت +۲۰)
    my_stam = min(a_max_stam if is_attacker else d_max_stam, my_stam + 20)

    # آپدیت دیتابیس
    if is_attacker:
        await update_fight(fight_id, attacker_hp=my_hp, defender_hp=opp_hp,
                           attacker_stamina=my_stam)
    else:
        await update_fight(fight_id, attacker_hp=opp_hp, defender_hp=my_hp,
                           defender_stamina=my_stam)

    fight = await get_fight(fight_id)

    if fight_ended:
        loser_id = opponent_id
        await end_fight(fight_id, "finished")
        panel_data_saved = context.bot_data.get(f"fight_panel_{fight_id}", {})
        await _give_rewards(
            context, winner_id, loser_id, attacker, defender, "pvp",
            fight["chat_id"], result_msgs, query=query
        )
        context.bot_data.pop(f"fight_panel_{fight_id}", None)
        return

    # نوبت بعدی + چک نوبت اضافه
    next_turn = opponent_id
    extra = check_extra_turn(my_player.stats.spd)
    if extra > 0:
        next_turn = user_id
        result_msgs.append(f"💨 **نوبت اضافه!** ({extra} بار دیگه میزنی)")

    await update_fight(fight_id, current_turn=next_turn)
    fight = await get_fight(fight_id)

    # ساخت پیام نتیجه
    result_text = "\n".join(result_msgs) if result_msgs else ""
    panel_text = build_fight_panel(
        fight, a_name, d_name, a_max_hp, d_max_hp, a_max_stam, d_max_stam, is_pvp
    )
    full_text = result_text + "\n━━━━━━━━━━━━━━━━━━━━━\n" + panel_text if result_text else panel_text

    # دکمه‌ها برای نفر بعدی
    next_player = attacker if next_turn == attacker_id else defender
    next_weapon, _ = await get_player_weapon_info(next_turn)
    next_stam_costs = get_stamina_costs(next_weapon)
    next_has_double = get_weapon_category(next_weapon) == "dagger"
    next_stam = fight["attacker_stamina"] if next_turn == attacker_id else fight["defender_stamina"]

    # برای pvp هر دو میتونن دکمه ببینن ولی فقط نفر نوبتی میتونه بزنه
    keyboard = build_fight_keyboard(fight_id, next_turn, fight, next_stam_costs, next_has_double, next_stam, is_pvp)

    await query.answer()
    try:
        await query.edit_message_text(full_text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass


async def _show_fight_potion_menu(query, context, fight_id: int, user_id: int):
    """نمایش منوی پوشن در فایت"""
    fight = await get_fight(fight_id)
    is_attacker = user_id == fight["attacker_id"]
    pot_used = fight["attacker_potions"] if is_attacker else fight["defender_potions"]

    if pot_used >= FIGHT_MAX_POTIONS:
        await query.answer(f"❌ حداکثر {FIGHT_MAX_POTIONS} پوشن مجازه!", show_alert=True)
        return

    inventory = await get_inventory(user_id)
    potions = [i for i in inventory if i.item_type == "consumable" and i.quantity > 0]

    if not potions:
        await query.answer("❌ پوشنی نداری!", show_alert=True)
        return

    keyboard = []
    for pot in potions:
        keyboard.append([
            InlineKeyboardButton(
                f"🧪 {pot.item_name} ×{pot.quantity}",
                callback_data=f"fight_usepotion_{fight_id}_{pot.item_name}",
                style="success"
            )
        ])
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت", callback_data=f"fight_backtoboard_{fight_id}", style="primary")
    ])

    await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))


async def fight_use_potion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استفاده از پوشن در فایت"""
    query = update.callback_query
    user_id = query.from_user.id
    parts = query.data.split("_", 3)
    fight_id = int(parts[2])
    potion_name = parts[3]

    fight = await get_fight(fight_id)
    if not fight or fight["status"] != "active" or fight["current_turn"] != user_id:
        await query.answer("❌ نوبت تو نیست!", show_alert=True)
        return

    is_attacker = user_id == fight["attacker_id"]
    pot_used = fight["attacker_potions"] if is_attacker else fight["defender_potions"]

    if pot_used >= FIGHT_MAX_POTIONS:
        await query.answer(f"❌ بیشتر از {FIGHT_MAX_POTIONS} پوشن نمیشه!", show_alert=True)
        return

    # استفاده از پوشن
    stats = ITEM_STATS.get("consumable", {}).get(potion_name, {})
    heal_percent = stats.get("heal_percent", 0.33)

    panel_data = context.bot_data.get(f"fight_panel_{fight_id}", {})
    max_hp = panel_data.get("a_max_hp" if is_attacker else "d_max_hp", 1000)
    cur_hp = fight["attacker_hp"] if is_attacker else fight["defender_hp"]
    heal = int(max_hp * heal_percent)
    new_hp = min(max_hp, cur_hp + heal)

    await use_consumable(user_id, potion_name)

    if is_attacker:
        await update_fight(fight_id, attacker_hp=new_hp,
                           attacker_potions=pot_used + 1,
                           current_turn=fight["defender_id"])
    else:
        await update_fight(fight_id, defender_hp=new_hp,
                           defender_potions=pot_used + 1,
                           current_turn=fight["attacker_id"])

    fight = await get_fight(fight_id)
    a_name = panel_data.get("a_name", "بازیکن ۱")
    d_name = panel_data.get("d_name", "بازیکن ۲")
    a_max_hp = panel_data.get("a_max_hp", 1000)
    d_max_hp = panel_data.get("d_max_hp", 1000)
    a_max_stam = panel_data.get("a_max_stam", 100)
    d_max_stam = panel_data.get("d_max_stam", 100)

    result = f"🧪 **{a_name if is_attacker else d_name}** پوشن زد! +{heal} ❤️\n"
    panel_text = build_fight_panel(fight, a_name, d_name, a_max_hp, d_max_hp, a_max_stam, d_max_stam, True)

    next_turn = fight["current_turn"]
    next_weapon, _ = await get_player_weapon_info(next_turn)
    next_stam_costs = get_stamina_costs(next_weapon)
    next_has_double = get_weapon_category(next_weapon) == "dagger"
    next_stam = fight["attacker_stamina"] if next_turn == fight["attacker_id"] else fight["defender_stamina"]
    keyboard = build_fight_keyboard(fight_id, next_turn, fight, next_stam_costs, next_has_double, next_stam, True)

    await query.answer(f"✅ +{heal} جون!")
    await query.edit_message_text(
        result + "━━━━━━━━━━━━━━━━━━━━━\n" + panel_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def fight_back_to_board_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برگشت به پنل اصلی فایت"""
    query = update.callback_query
    fight_id = int(query.data.replace("fight_backtoboard_", ""))
    fight = await get_fight(fight_id)

    panel_data = context.bot_data.get(f"fight_panel_{fight_id}", {})
    a_name = panel_data.get("a_name", "۱")
    d_name = panel_data.get("d_name", "۲")
    a_max_hp = panel_data.get("a_max_hp", 1000)
    d_max_hp = panel_data.get("d_max_hp", 1000)
    a_max_stam = panel_data.get("a_max_stam", 100)
    d_max_stam = panel_data.get("d_max_stam", 100)

    user_id = query.from_user.id
    panel_text = build_fight_panel(fight, a_name, d_name, a_max_hp, d_max_hp, a_max_stam, d_max_stam, True)

    next_weapon, _ = await get_player_weapon_info(fight["current_turn"])
    stam_costs = get_stamina_costs(next_weapon)
    has_double = get_weapon_category(next_weapon) == "dagger"
    cur_stam = fight["attacker_stamina"] if fight["current_turn"] == fight["attacker_id"] else fight["defender_stamina"]
    keyboard = build_fight_keyboard(fight_id, fight["current_turn"], fight, stam_costs, has_double, cur_stam, True)

    await query.answer()
    await query.edit_message_text(panel_text, reply_markup=keyboard, parse_mode="Markdown")


# ==========================================
# پاداش و پایان فایت
# ==========================================
async def _give_rewards(context, winner_id: int, loser_id: int,
                        attacker: Player, defender: Player,
                        fight_type: str, chat_id: int, log: list, query=None):
    """اعمال پاداش برنده و جریمه بازنده"""
    winner = attacker if winner_id == attacker.user_id else defender
    loser = attacker if loser_id == attacker.user_id else defender

    loser_row = await get_user(loser_id)
    loser_player = Player.from_db_row(loser_row)

    gold_prize = int(loser_player.stats.gold * FIGHT_GOLD_RATIO)
    gold_prize = int(gold_prize * (1 + winner.stats.lck * 0.005))

    upgrade_prize = 0
    if fight_type == "pvp":
        loser_upgrades = await get_upgrade_points(loser_id)
        upgrade_prize = int(loser_upgrades * FIGHT_UPGRADE_RATIO)

    # اکس‌پی بر اساس اختلاف لول
    level_diff = abs(winner.stats.level - loser.stats.level)
    base_exp = 100 + level_diff * 30
    if fight_type == "forced":
        base_exp = int(base_exp * 0.4)
        gold_prize = int(gold_prize * 0.5)

    # اعمال پاداش‌ها
    conn = await get_db()
    await conn.execute("UPDATE users SET gold = gold + $1 WHERE user_id = $2", gold_prize, winner_id)
    await conn.execute("UPDATE users SET gold = GREATEST(0, gold - $1) WHERE user_id = $2", gold_prize, loser_id)
    await conn.close()

    if upgrade_prize > 0:
        await add_upgrade_points(winner_id, upgrade_prize)
        await remove_upgrade_points(loser_id, upgrade_prize)

    exp_result = await add_exp(winner_id, base_exp)

    # شیلد و HP بازنده
    await set_fight_shield(loser_id, FIGHT_SHIELD_MINUTES)
    loser_new_hp = max(1, loser_player.stats.max_hp // 2)
    await update_user_hp(loser_id, loser_new_hp)

    # ساخت پیام نتیجه
    log_text = "\n".join(log[-6:]) if log else ""  # آخرین ۶ خط لاگ
    fight_type_text = "تن به تن ⚔️" if fight_type == "pvp" else "فایت زوری 🤖"

    result_msg = (
        f"🏆 **پایان نبرد** | {fight_type_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
    )
    if log_text:
        result_msg += f"{log_text}\n━━━━━━━━━━━━━━━━━━━━━\n"

    result_msg += (
        f"👑 **برنده: {winner.character_name}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 +{gold_prize} سکه\n"
    )
    if upgrade_prize > 0:
        result_msg += f"⭐ +{upgrade_prize} آپگرید پوینت\n"
    result_msg += f"✨ +{base_exp} اکس‌پی\n"

    if exp_result and exp_result.get("leveled_up"):
        result_msg += f"🎉 لول آپ! ⭐ لول {exp_result['new_level']}\n"

    result_msg += (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"😔 **بازنده: {loser.character_name}**\n"
        f"🛡️ شیلد {FIGHT_SHIELD_MINUTES} دقیقه\n"
        f"❤️ HP از نصف پر شد"
    )

    if query:
        try:
            await query.edit_message_text(result_msg, parse_mode="Markdown")
            return
        except Exception:
            pass

    await context.bot.send_message(chat_id, result_msg, parse_mode="Markdown")
