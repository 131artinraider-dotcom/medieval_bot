from handlers.panel_utils import register_panel
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_user, get_inventory, get_equipped, 
    equip_item, use_consumable, update_user_hp,
    get_item_quantity, can_equip_item
)
from models import Player, Item
from config import ITEM_STATS, CLASSES

# ===== تابع کمکی برای ساخت صفحه‌بندی =====
def paginate_items(items, page: int = 0, items_per_page: int = 5):
    total_items = len(items)
    total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
    start = page * items_per_page
    end = min(start + items_per_page, total_items)
    page_items = items[start:end]
    return page_items, total_pages, page

# ===== پنل اصلی اینونتوری =====
async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await update.message.reply_text(
            "❌ شما هنوز شخصیت خودت رو نساختی!\n"
            "برای شروع از /start یا 'شروع' استفاده کن."
        )
        return
    
    # دریافت آیتم‌ها
    items = await get_inventory(user_id)
    equipped = await get_equipped(user_id)
    
    all_items = Item.from_db_list(items)
    equipped_items = Item.from_db_list(equipped)
    
    weapons = [item for item in all_items if item.item_type == 'weapon']
    armors = [item for item in all_items if item.item_type == 'armor']
    consumables = [item for item in all_items if item.item_type == 'consumable']
    
    equipped_weapon = next((item for item in equipped_items if item.item_type == 'weapon'), None)
    equipped_armor = next((item for item in equipped_items if item.item_type == 'armor'), None)
    
    # ساخت پیام
    msg = f"📦 **اینونتوری {player.character_name}**\n\n"
    msg += f"❤️ **جون**: {player.stats.hp} / {player.stats.max_hp}\n"
    msg += f"`{player.get_hp_bar()}`\n\n"
    msg += f"📈 **اکس‌پی**: {player.stats.exp} / {player.stats.max_exp}\n"
    msg += f"`{player.get_exp_bar()}`\n\n"
    msg += f"⭐ **سطح**: {player.stats.level}  |  💰 **طلا**: {player.stats.gold}\n\n"
    
    msg += "---\n"
    msg += "🛡️ **تجهیزات فعلی:**\n"
    if equipped_weapon:
        msg += f"🗡️ {equipped_weapon.item_name} (تجهیز)\n"
    else:
        msg += "🗡️ هیچ سلاحی تجهیز نشده\n"
    
    if equipped_armor:
        msg += f"🛡️ {equipped_armor.item_name} (تجهیز)\n"
    else:
        msg += "🛡️ هیچ زره‌ای تجهیز نشده\n"
    
    msg += "\n---\n"
    
    if weapons:
        msg += "⚔️ **سلاح‌ها:**\n"
        for w in weapons:
            if w.equipped:
                msg += f"- {w.item_name} ×{w.quantity} 🔒 (تجهیز)\n"
            else:
                msg += f"- {w.item_name} ×{w.quantity}\n"
    else:
        msg += "⚔️ **سلاح‌ها:** خالی\n"
    
    msg += "\n"
    
    if armors:
        msg += "🛡️ **زره‌ها:**\n"
        for a in armors:
            if a.equipped:
                msg += f"- {a.item_name} ×{a.quantity} 🔒 (تجهیز)\n"
            else:
                msg += f"- {a.item_name} ×{a.quantity}\n"
    else:
        msg += "🛡️ **زره‌ها:** خالی\n"
    
    msg += "\n"
    
    if consumables:
        msg += "🧪 **مصرفی‌ها:**\n"
        for c in consumables:
            msg += f"- {c.get_display_name()} ×{c.quantity}\n"
    else:
        msg += "🧪 **مصرفی‌ها:** خالی\n"
    
    # دکمه‌های رنگی
    keyboard = [
        [InlineKeyboardButton("⚔️ تجهیز سلاح", callback_data="inv_equip_weapon", style="success")],
        [InlineKeyboardButton("🛡️ تجهیز زره", callback_data="inv_equip_armor", style="primary")],
        [InlineKeyboardButton("🧪 استفاده آیتم", callback_data="inv_use_item", style="primary")],
        [InlineKeyboardButton("🔙 بستن پنل", callback_data="inv_close", style="danger")]
    ]
    
    _msg = await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    if _msg:
        register_panel(_msg.message_id, update.effective_user.id, context)

# ===== نمایش لیست سلاح‌ها برای تجهیز =====
async def equip_weapon_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    query = update.callback_query
    user_id = query.from_user.id
    
    items = await get_inventory(user_id)
    all_items = Item.from_db_list(items)
    
    weapons = [
        item for item in all_items 
        if item.item_type == 'weapon' and not item.equipped and item.quantity > 0
    ]
    
    if not weapons:
        await query.edit_message_text(
            "❌ هیچ سلاح قابل تجهیزی نداری!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
            ])
        )
        return
    
    page_items, total_pages, current_page = paginate_items(weapons, page)
    
    keyboard = []
    for w in page_items:
        btn_text = f"{w.item_name} (×{w.quantity})"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"inv_equip_weapon_{w.item_name}")
        ])
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"inv_weapon_page_{current_page-1}"))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"inv_weapon_page_{current_page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")])
    
    await query.edit_message_text(
        f"⚔️ **تجهیز سلاح** (صفحه {current_page+1}/{total_pages})\n\n"
        "⚠️ برای تجهیز هر سلاح باید لول‌های مورد نیاز رو داشته باشی.\n"
        "یکی از سلاح‌های زیر رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== نمایش لیست زره‌ها برای تجهیز =====
async def equip_armor_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    query = update.callback_query
    user_id = query.from_user.id
    
    items = await get_inventory(user_id)
    all_items = Item.from_db_list(items)
    
    armors = [
        item for item in all_items 
        if item.item_type == 'armor' and not item.equipped and item.quantity > 0
    ]
    
    if not armors:
        await query.edit_message_text(
            "❌ هیچ زره قابل تجهیزی نداری!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
            ])
        )
        return
    
    page_items, total_pages, current_page = paginate_items(armors, page)
    
    keyboard = []
    for a in page_items:
        btn_text = f"{a.item_name} (×{a.quantity})"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"inv_equip_armor_{a.item_name}")
        ])
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"inv_armor_page_{current_page-1}"))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"inv_armor_page_{current_page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")])
    
    await query.edit_message_text(
        f"🛡️ **تجهیز زره** (صفحه {current_page+1}/{total_pages})\n\n"
        "⚠️ برای تجهیز هر زره باید لول دفاع مورد نیاز رو داشته باشی.\n"
        "یکی از زره‌های زیر رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== نمایش لیست آیتم‌های مصرفی =====
async def use_item_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    query = update.callback_query
    user_id = query.from_user.id
    
    items = await get_inventory(user_id)
    all_items = Item.from_db_list(items)
    
    consumables = [
        item for item in all_items 
        if item.item_type == 'consumable' and item.quantity > 0
    ]
    
    if not consumables:
        await query.edit_message_text(
            "❌ هیچ آیتم مصرفی‌ای نداری!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
            ])
        )
        return
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    page_items, total_pages, current_page = paginate_items(consumables, page)
    
    msg = f"🧪 **استفاده آیتم** (صفحه {current_page+1}/{total_pages})\n\n"
    msg += f"❤️ **جون فعلی**: {player.stats.hp} / {player.stats.max_hp}\n"
    msg += f"`{player.get_hp_bar()}`\n\n"
    msg += "**توضیحات آیتم‌ها:**\n"
    
    keyboard = []
    for c in page_items:
        stats = c.get_stats()
        if "heal_percent" in stats:
            percent = int(stats['heal_percent'] * 100)
            msg += f"• {c.get_display_name()}: ❤️ {percent}% جون رو پر میکنه\n"
            btn_text = f"{c.get_display_name()} (×{c.quantity})"
            keyboard.append([
                InlineKeyboardButton(btn_text, callback_data=f"inv_use_consumable_{c.item_name}_{c.level}")
            ])
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"inv_consumable_page_{current_page-1}"))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"inv_consumable_page_{current_page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")])
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== تایید استفاده از آیتم =====
async def confirm_use_consumable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    item_name = parts[3]
    level = int(parts[4])
    user_id = query.from_user.id
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    item_stats = ITEM_STATS.get('consumable', {}).get(item_name, {})
    heal_percent = item_stats.get('heal_percent', 0)
    
    heal_amount = int(player.stats.max_hp * heal_percent)
    new_hp = min(player.stats.hp + heal_amount, player.stats.max_hp)
    
    used_item = await use_consumable(user_id, item_name, level)
    
    if not used_item:
        await query.edit_message_text("❌ این آیتم موجود نیست!")
        return
    
    await update_user_hp(user_id, new_hp)
    
    # آپدیت مجدد برای نمایش نوار درست
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    await query.edit_message_text(
        f"✅ **از {item_name} استفاده شد!**\n\n"
        f"❤️ {heal_amount} جون بهت اضافه شد!\n"
        f"❤️ **جون جدید**: {new_hp} / {player.stats.max_hp}\n"
        f"`{player.get_hp_bar()}`\n\n"
        f"برای ادامه به اینونتوری برگرد.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
        ])
    )

# ===== اجرای تجهیز سلاح (با چک کردن لول‌ها) =====
async def execute_equip_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای تجهیز سلاح با چک کردن لول‌های مورد نیاز"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    item_name = data.replace("inv_equip_weapon_", "")
    user_id = query.from_user.id
    
    # ===== چک کردن لول‌های مورد نیاز =====
    can_equip_result = await can_equip_item(user_id, item_name)
    
    if not can_equip_result["can"]:
        await query.edit_message_text(
            f"{can_equip_result['message']}\n\n"
            "برای برگشت به اینونتوری دکمه زیر رو بزن.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
            ])
        )
        return
    
    # ===== اجرای تجهیز =====
    result = await equip_item(user_id, 'weapon', item_name)
    
    if not result["can"]:
        await query.edit_message_text(
            result["message"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
            ])
        )
        return
    
    await query.edit_message_text(
        f"✅ **{item_name} تجهیز شد!**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
        ])
    )

# ===== اجرای تجهیز زره (با چک کردن لول‌ها) =====
async def execute_equip_armor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای تجهیز زره با چک کردن لول‌های مورد نیاز"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    item_name = data.replace("inv_equip_armor_", "")
    user_id = query.from_user.id
    
    # ===== چک کردن لول‌های مورد نیاز =====
    can_equip_result = await can_equip_item(user_id, item_name)
    
    if not can_equip_result["can"]:
        await query.edit_message_text(
            f"{can_equip_result['message']}\n\n"
            "برای برگشت به اینونتوری دکمه زیر رو بزن.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
            ])
        )
        return
    
    # ===== اجرای تجهیز =====
    result = await equip_item(user_id, 'armor', item_name)
    
    if not result["can"]:
        await query.edit_message_text(
            result["message"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
            ])
        )
        return
    
    await query.edit_message_text(
        f"✅ **{item_name} تجهیز شد!**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت به اینونتوری", callback_data="inv_back_to_inventory", style="primary")]
        ])
    )

# ===== نمایش پنل اینونتوری (کمکی) =====
async def show_inventory_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await query.edit_message_text("❌ شما هنوز شخصیت خودت رو نساختی!", parse_mode="Markdown")
        return
    
    items = await get_inventory(user_id)
    equipped = await get_equipped(user_id)
    
    all_items = Item.from_db_list(items)
    equipped_items = Item.from_db_list(equipped)
    
    weapons = [item for item in all_items if item.item_type == 'weapon']
    armors = [item for item in all_items if item.item_type == 'armor']
    consumables = [item for item in all_items if item.item_type == 'consumable']
    
    equipped_weapon = next((item for item in equipped_items if item.item_type == 'weapon'), None)
    equipped_armor = next((item for item in equipped_items if item.item_type == 'armor'), None)
    
    msg = f"📦 **اینونتوری {player.character_name}**\n\n"
    msg += f"❤️ **جون**: {player.stats.hp} / {player.stats.max_hp}\n"
    msg += f"`{player.get_hp_bar()}`\n\n"
    msg += f"📈 **اکس‌پی**: {player.stats.exp} / {player.stats.max_exp}\n"
    msg += f"`{player.get_exp_bar()}`\n\n"
    msg += f"⭐ **سطح**: {player.stats.level}  |  💰 **طلا**: {player.stats.gold}\n\n"
    
    msg += "---\n"
    msg += "🛡️ **تجهیزات فعلی:**\n"
    if equipped_weapon:
        msg += f"🗡️ {equipped_weapon.item_name} (تجهیز)\n"
    else:
        msg += "🗡️ هیچ سلاحی تجهیز نشده\n"
    
    if equipped_armor:
        msg += f"🛡️ {equipped_armor.item_name} (تجهیز)\n"
    else:
        msg += "🛡️ هیچ زره‌ای تجهیز نشده\n"
    
    msg += "\n---\n"
    
    if weapons:
        msg += "⚔️ **سلاح‌ها:**\n"
        for w in weapons:
            if w.equipped:
                msg += f"- {w.item_name} ×{w.quantity} 🔒 (تجهیز)\n"
            else:
                msg += f"- {w.item_name} ×{w.quantity}\n"
    else:
        msg += "⚔️ **سلاح‌ها:** خالی\n"
    
    msg += "\n"
    
    if armors:
        msg += "🛡️ **زره‌ها:**\n"
        for a in armors:
            if a.equipped:
                msg += f"- {a.item_name} ×{a.quantity} 🔒 (تجهیز)\n"
            else:
                msg += f"- {a.item_name} ×{a.quantity}\n"
    else:
        msg += "🛡️ **زره‌ها:** خالی\n"
    
    msg += "\n"
    
    if consumables:
        msg += "🧪 **مصرفی‌ها:**\n"
        for c in consumables:
            msg += f"- {c.get_display_name()} ×{c.quantity}\n"
    else:
        msg += "🧪 **مصرفی‌ها:** خالی\n"
    
    keyboard = [
        [InlineKeyboardButton("⚔️ تجهیز سلاح", callback_data="inv_equip_weapon", style="success")],
        [InlineKeyboardButton("🛡️ تجهیز زره", callback_data="inv_equip_armor", style="primary")],
        [InlineKeyboardButton("🧪 استفاده آیتم", callback_data="inv_use_item", style="primary")],
        [InlineKeyboardButton("🔙 بستن پنل", callback_data="inv_close", style="danger")]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== بستن پنل =====
async def close_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.delete_message()

