from handlers.panel_utils import register_panel
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_user, get_inventory, get_shop_items_by_category,
    get_shop_armors, get_shop_consumables, get_shop_item_by_name,
    buy_item, sell_item, get_sellable_items, can_equip_item,
    update_quest_progress  # ← اضافه کن
)
from models import Player, Item
from config import CATEGORIES, SELL_PRICE_RATIO, WEAPON_BONUSES

# ===== تابع کمکی برای دریافت بونوس سلاح =====
def get_weapon_bonus_info(item_name: str):
    """دریافت اطلاعات بونوس یک سلاح"""
    for category, bonus_data in WEAPON_BONUSES.items():
        if category in ["sword", "katana", "dagger", "axe"]:
            chances = bonus_data.get('chances', {})
            if item_name in chances:
                chance = chances[item_name]
                return {
                    "emoji": bonus_data['emoji'],
                    "name": bonus_data['name'],
                    "chance": chance,
                    "type": bonus_data['type']
                }
    return None

# ===== تابع کمکی برای صفحه‌بندی =====
def paginate_items(items, page: int = 0, items_per_page: int = 3):
    total_items = len(items)
    total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
    start = page * items_per_page
    end = min(start + items_per_page, total_items)
    page_items = items[start:end]
    return page_items, total_pages, page

# ===== تابع کمکی برای نمایش پنل اصلی شاپ (از کالبک) =====
async def show_shop_panel(query, user_id: int):
    """نمایش پنل اصلی شاپ (برای کالبک‌ها)"""
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await query.edit_message_text("❌ شما هنوز شخصیت خودت رو نساختی!")
        return
    
    msg = (
        f"🏪 **فروشگاه قرون وسطی**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 سکه‌های تو: {player.stats.gold:,}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"یکی از گزینه‌های زیر رو انتخاب کن:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🗡️ خرید سلاح", callback_data="shop_buy_weapon", style="success"),
            InlineKeyboardButton("🛡️ خرید زره", callback_data="shop_buy_armor", style="primary"),
        ],
        [
            InlineKeyboardButton("🧪 خرید آیتم", callback_data="shop_buy_item", style="primary"),
            InlineKeyboardButton("💰 فروش آیتم", callback_data="shop_sell", style="primary"),
        ],
        [InlineKeyboardButton("🔙 بستن پنل", callback_data="shop_close", style="danger")]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== پنل اصلی شاپ (از کامند) =====
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل اصلی فروشگاه (از کامند)"""
    user_id = update.effective_user.id
    
    user_row = await get_user(user_id)
    player = Player.from_db_row(user_row)
    
    if not player or not player.is_registered:
        await update.message.reply_text(
            "❌ شما هنوز شخصیت خودت رو نساختی!\n"
            "برای شروع از /start یا 'شروع' استفاده کن."
        )
        return
    
    msg = (
        f"🏪 **فروشگاه قرون وسطی**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 سکه‌های تو: {player.stats.gold:,}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"یکی از گزینه‌های زیر رو انتخاب کن:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🗡️ خرید سلاح", callback_data="shop_buy_weapon", style="success"),
            InlineKeyboardButton("🛡️ خرید زره", callback_data="shop_buy_armor", style="primary"),
        ],
        [
            InlineKeyboardButton("🧪 خرید آیتم", callback_data="shop_buy_item", style="primary"),
            InlineKeyboardButton("💰 فروش آیتم", callback_data="shop_sell", style="primary"),
        ],
        [InlineKeyboardButton("🔙 بستن پنل", callback_data="shop_close", style="danger")]
    ]
    
    _msg = await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    if _msg:
        register_panel(_msg.message_id, update.effective_user.id, context, update.effective_chat.id)

# ===== بخش خرید سلاح (مرحله اول - انتخاب دسته‌بندی) =====
async def shop_buy_weapon_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش دسته‌بندی‌های سلاح"""
    query = update.callback_query
    await query.answer()
    
    categories = ["sword", "katana", "dagger", "axe"]
    msg = "🗡️ **دسته‌بندی سلاح‌ها**\n━━━━━━━━━━━━━━━━━━━━━\n"
    for cat in categories:
        info = CATEGORIES.get(cat, {})
        bonus = WEAPON_BONUSES.get(cat, {})
        bonus_txt = f" | {bonus['emoji']} {bonus['name']}" if bonus else ""
        msg += f"{info.get('emoji','')} **{info.get('name',cat)}**: {info.get('desc','')} {bonus_txt}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\nانتخاب کن:"

    keyboard = []
    for cat in categories:
        info = CATEGORIES.get(cat, {})
        keyboard.append([
            InlineKeyboardButton(
                f"{info.get('emoji', '')} {info.get('name', cat)}",
                callback_data=f"shop_buy_weapons_{cat}",
                style="primary"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="danger")
    ])
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== بخش خرید سلاح (مرحله دوم - لیست سلاح‌های دسته با بونوس) =====
async def shop_buy_weapons(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """نمایش لیست سلاح‌های یک دسته با صفحه‌بندی ۳ تایی و بونوس"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    category = data.replace("shop_buy_weapons_", "").split("_page")[0]
    
    items = await get_shop_items_by_category(category)
    
    if not items:
        await query.edit_message_text(
            f"❌ هیچ سلاحی در این دسته وجود ندارد!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="shop_buy_weapon", style="primary")]
            ])
        )
        return
    
    page_items, total_pages, current_page = paginate_items(items, page, 3)
    
    cat_info = CATEGORIES.get(category, {})
    msg = f"{cat_info.get('emoji', '')} **{cat_info.get('name', category)}** (صفحه {current_page+1}/{total_pages})\n\n"
    
    for item in page_items:
        req_text = []
        if item['level_required_atk'] > 0:
            req_text.append(f"اتک {item['level_required_atk']}")
        if item['level_required_def'] > 0:
            req_text.append(f"دفاع {item['level_required_def']}")
        if item['level_required_spd'] > 0:
            req_text.append(f"سرعت {item['level_required_spd']}")
        if item['level_required_lck'] > 0:
            req_text.append(f"شانس {item['level_required_lck']}")
        
        req_str = "، ".join(req_text) if req_text else "بدون نیاز"
        
        # ===== دریافت بونوس سلاح =====
        bonus_info = get_weapon_bonus_info(item['item_name'])
        bonus_text = ""
        if bonus_info:
            chance_percent = int(bonus_info['chance'] * 100)
            bonus_text = f"\n   🎯 بونوس: {bonus_info['emoji']} {bonus_info['name']} ({chance_percent}%)"
        
        # ===== دریافت اثر از ITEM_STATS =====
        from config import ITEM_STATS
        weapon_stats = ITEM_STATS.get('weapon', {}).get(item['item_name'], {})
        atk_bonus = weapon_stats.get('atk_bonus', 0)
        
        msg += (
            f"🔹 **{item['item_name']}** | 💰 {item['price']:,} | ⚔️ +{atk_bonus}{bonus_text}\n"
            f"   📋 نیاز: {req_str}\n"
        )
    
    keyboard = []
    for item in page_items:
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 خرید {item['item_name']}",
                callback_data=f"shop_buy_execute_{item['item_name']}",
                style="success"
            )
        ])
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "◀️", 
            callback_data=f"shop_buy_weapons_{category}_page_{current_page-1}"
        ))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            "▶️", 
            callback_data=f"shop_buy_weapons_{category}_page_{current_page+1}"
        ))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت به دسته‌بندی", callback_data="shop_buy_weapon", style="primary")
    ])
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== بخش خرید زره (یک مرحله‌ای با صفحه‌بندی ۵ تایی) =====
async def shop_buy_armors(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """نمایش لیست زره‌ها با صفحه‌بندی ۵ تایی"""
    query = update.callback_query
    await query.answer()
    
    items, total = await get_shop_armors(page, 5)
    total_pages = (total + 4) // 5 if total > 0 else 1
    
    if not items:
        await query.edit_message_text(
            "❌ هیچ زره‌ای در شاپ موجود نیست!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="primary")]
            ])
        )
        return
    
    msg = f"🛡️ **زره‌ها** (صفحه {page+1}/{total_pages})\n\n"
    
    for item in items:
        req_text = []
        if item['level_required_def'] > 0:
            req_text.append(f"دفاع {item['level_required_def']}")
        
        req_str = "، ".join(req_text) if req_text else "بدون نیاز"
        
        # ===== دریافت اثر از ITEM_STATS =====
        from config import ITEM_STATS
        armor_stats = ITEM_STATS.get('armor', {}).get(item['item_name'], {})
        def_bonus = armor_stats.get('def_bonus', 0)
        
        msg += (
            f"🔹 **{item['item_name']}** | 💰 {item['price']:,} | 🛡️ +{def_bonus}\n"
            f"   📋 نیاز: {req_str}\n"
        )
    
    keyboard = []
    for item in items:
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 خرید {item['item_name']}",
                callback_data=f"shop_buy_execute_{item['item_name']}",
                style="success"
            )
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"shop_buy_armor_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"shop_buy_armor_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="primary")
    ])
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== بخش خرید آیتم (مرحله اول - انتخاب دسته) =====
async def shop_buy_item_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش دسته‌بندی آیتم‌ها"""
    query = update.callback_query
    await query.answer()
    
    msg = (
        "🧪 **آیتم‌ها**\n━━━━━━━━━━━━━━━━━━━━━\n"
        "🧪 پوشن‌های جون: جون رو پر میکنن (لول ۱ تا ۳)\n"
        "━━━━━━━━━━━━━━━━━━━━━\nانتخاب کن:"
    )
    
    keyboard = [
        [InlineKeyboardButton("🧪 پوشن‌های جون", callback_data="shop_buy_consumables", style="primary")],
        [InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="danger")]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== بخش خرید پوشن‌ها با قابلیت انتخاب تعداد =====
async def shop_buy_consumables(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست پوشن‌ها با قابلیت انتخاب تعداد"""
    query = update.callback_query
    await query.answer()
    
    items = await get_shop_consumables()
    
    if not items:
        await query.edit_message_text(
            "❌ هیچ آیتم مصرفی‌ای در شاپ موجود نیست!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="shop_buy_item", style="primary")]
            ])
        )
        return
    
    msg = "🧪 **پوشن‌های جون**\n━━━━━━━━━━━━━━━━━━━━━\n"
    
    for item in items:
        heal_percent = int(item['heal_percent'] * 100) if item['heal_percent'] > 0 else 0
        msg += f"🔹 **{item['item_name']}** | 💰 {item['price']:,} | ❤️ {heal_percent}%\n"
    
    keyboard = []
    for item in items:
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 خرید {item['item_name']}",
                callback_data=f"shop_buy_quantity_{item['item_name']}",
                style="success"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت به دسته‌بندی", callback_data="shop_buy_item", style="primary")
    ])
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ===== دریافت تعداد از کاربر =====
async def shop_buy_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت تعداد آیتم برای خرید با نمایش جزئیات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    item_name = query.data.replace("shop_buy_quantity_", "")
    context.user_data['buy_item_name'] = item_name
    
    # دریافت اطلاعات کاربر و آیتم
    user_row = await get_user(user_id)
    shop_item = await get_shop_item_by_name(item_name)
    
    if not shop_item:
        await query.edit_message_text("❌ آیتم مورد نظر موجود نیست!")
        return
    
    price = shop_item['price']
    user_gold = user_row['gold']
    max_buy = user_gold // price
    
    # دریافت اثر آیتم
    from config import ITEM_STATS
    if shop_item['item_type'] == 'consumable':
        heal_percent = int(shop_item['heal_percent'] * 100) if shop_item['heal_percent'] > 0 else 0
        effect_text = f"❤️ {heal_percent}% جون رو پر میکنه"
    else:
        effect_text = "⚔️ آیتم جنگی"
    
    msg = (
        f"📝 **خرید {item_name}**\n\n"
        f"💰 قیمت هر عدد: {price:,} سکه\n"
        f"💰 سکه‌های تو: {user_gold:,}\n"
        f"📦 حداکثر قابل خرید: {max_buy} عدد\n"
        f"✨ اثر: {effect_text}\n\n"
        f"تعداد مورد نظر رو وارد کن:"
    )
    
    keyboard = [
        [InlineKeyboardButton("❌ لغو عملیات", callback_data="shop_cancel_buy", style="danger")]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )





# ===== لغو خرید =====
async def shop_cancel_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو عملیات خرید"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.pop('buy_item_name', None)
    
    await query.edit_message_text(
        "❌ عملیات خرید لغو شد.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="primary")]
        ])
    )






# ===== اجرای خرید با تعداد =====
async def shop_execute_quantity_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای خرید با تعداد مشخص"""
    user_id = update.effective_user.id
    item_name = context.user_data.get('buy_item_name')
    
    if not item_name:
        await update.message.reply_text("❌ لطفاً دوباره از شاپ انتخاب کن.")
        return
    
    try:
        quantity = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کن!")
        return
    
    if quantity < 1:
        await update.message.reply_text("❌ حداقل ۱ عدد!")
        return
    
    if quantity > 100:
        await update.message.reply_text("❌ حداکثر ۱۰۰ عدد!")
        return
    
    # دریافت قیمت آیتم
    shop_item = await get_shop_item_by_name(item_name)
    if not shop_item:
        await update.message.reply_text("❌ آیتم مورد نظر موجود نیست!")
        context.user_data.pop('buy_item_name', None)
        return
    
    price = shop_item['price']
    total_cost = price * quantity
    
    # بررسی سکه کاربر
    user_row = await get_user(user_id)
    if user_row['gold'] < total_cost:
        max_buy = user_row['gold'] // price
        await update.message.reply_text(
            f"❌ سکه کافی نیست!\n\n"
            f"💰 نیاز: {total_cost:,} سکه\n"
            f"💰 داری: {user_row['gold']:,} سکه\n"
            f"📦 حداکثر می‌تونی {max_buy} عدد بخری."
        )
        return
    
    # ===== اجرای خرید =====
    success_count = 0
    for i in range(quantity):
        result = await buy_item(user_id, item_name)
        if result["success"]:
            success_count += 1
        else:
            break
    
    if success_count == 0:
        await update.message.reply_text("❌ خرید انجام نشد!")
        context.user_data.pop('buy_item_name', None)
        return
    
    # ===== آپدیت پیشرفت کوئست =====
    await update_quest_progress(user_id, "shop", success_count)
    
    # دریافت سکه جدید
    user_row = await get_user(user_id)
    
    # دریافت اثر آیتم
    from config import ITEM_STATS
    if shop_item['item_type'] == 'consumable':
        heal_percent = int(shop_item['heal_percent'] * 100) if shop_item['heal_percent'] > 0 else 0
        effect_text = f"❤️ {heal_percent}% جون رو پر میکنه"
    else:
        effect_text = "⚔️ آیتم جنگی"
    
    msg = (
        f"✅ **{success_count} عدد {item_name} خریداری شد!**\n\n"
        f"💰 هزینه کل: {total_cost:,} سکه\n"
        f"💰 سکه باقی‌مونده: {user_row['gold']:,} سکه\n"
        f"✨ اثر: {effect_text}\n\n"
        f"تعداد خریداری شده به اینونتوری اضافه شد."
    )
    
    context.user_data.pop('buy_item_name', None)
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="primary")]
    ]
    
    _msg = await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    if _msg:
        register_panel(_msg.message_id, update.effective_user.id, context, update.effective_chat.id)









# ===== بخش فروش آیتم =====
async def shop_sell_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش دسته‌بندی برای فروش"""
    query = update.callback_query
    await query.answer()
    
    msg = (
        "💰 **فروش آیتم**\n━━━━━━━━━━━━━━━━━━━━━\n"
        "آیتم‌ها با نصف قیمت فروخته میشن.\n"
        "━━━━━━━━━━━━━━━━━━━━━\nانتخاب کن:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🗡️ سلاح‌ها", callback_data="shop_sell_weapon", style="primary"),
            InlineKeyboardButton("🛡️ زره‌ها", callback_data="shop_sell_armor", style="primary"),
        ],
        [
            InlineKeyboardButton("🧪 آیتم‌ها", callback_data="shop_sell_consumable", style="primary"),
            InlineKeyboardButton("🔙 برگشت", callback_data="shop_back_to_main", style="danger"),
        ]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== بخش فروش (نمایش آیتم‌های قابل فروش) =====
async def shop_sell_items(update: Update, context: ContextTypes.DEFAULT_TYPE, item_type: str, page: int = 0):
    """نمایش آیتم‌های قابل فروش"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    items = await get_sellable_items(user_id, item_type)
    
    if not items:
        type_names = {
            "weapon": "سلاح",
            "armor": "زره",
            "consumable": "آیتم"
        }
        await query.edit_message_text(
            f"❌ هیچ {type_names.get(item_type, 'آیتم')} قابل فروشی نداری!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="shop_sell", style="primary")]
            ])
        )
        return
    
    page_items, total_pages, current_page = paginate_items(items, page, 3)
    
    type_names = {
        "weapon": "🗡️ سلاح‌ها",
        "armor": "🛡️ زره‌ها",
        "consumable": "🧪 آیتم‌ها"
    }
    
    msg = f"💰 **فروش {type_names.get(item_type, 'آیتم')}** (صفحه {current_page+1}/{total_pages})\n\n"
    
    for item in page_items:
        shop_item = await get_shop_item_by_name(item['item_name'])
        sell_price = int(shop_item['price'] * SELL_PRICE_RATIO) if shop_item else 0
        
        msg += f"🔹 **{item['item_name']}** ×{item['quantity']} | 💰 {sell_price:,}\n"
    
    keyboard = []
    for item in page_items:
        shop_item = await get_shop_item_by_name(item['item_name'])
        sell_price = int(shop_item['price'] * SELL_PRICE_RATIO) if shop_item else 0
        
        keyboard.append([
            InlineKeyboardButton(
                f"💰 فروش {item['item_name']} ({sell_price:,})",
                callback_data=f"shop_sell_execute_{item['item_name']}_{item['level']}",
                style="success"
            )
        ])
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"shop_sell_{item_type}_page_{current_page-1}"))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"shop_sell_{item_type}_page_{current_page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("🔙 برگشت", callback_data="shop_sell", style="primary")
    ])
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )



# ===== اجرای خرید (یک عدد) =====
async def execute_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای خرید با تایمر ۱۰ ثانیه (برای سلاح و زره)"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    item_name = data.replace("shop_buy_execute_", "")
    user_id = query.from_user.id
    
    result = await buy_item(user_id, item_name)
    
    if not result["success"]:
        await query.edit_message_text(
            result["message"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="primary")]
            ])
        )
        return
    
    # ===== آپدیت پیشرفت کوئست =====
    await update_quest_progress(user_id, "shop")
    
    msg = (
        f"{result['message']}\n\n"
        f"💰 سکه‌های جدید: {result['new_gold']:,}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="primary")]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )




# ===== اجرای فروش =====
async def execute_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای فروش با تایمر ۱۰ ثانیه"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.replace("shop_sell_execute_", "").split("_")
    item_name = "_".join(parts[:-1])
    level = int(parts[-1])
    user_id = query.from_user.id
    
    result = await sell_item(user_id, item_name, level)
    
    if not result["success"]:
        await query.edit_message_text(
            result["message"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="primary")]
            ])
        )
        return
    
    msg = (
        f"{result['message']}\n\n"
        f"💰 سکه‌های جدید: {result['new_gold']:,}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت به شاپ", callback_data="shop_back_to_main", style="primary")]
    ]
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== برگشت به پنل اصلی =====
async def shop_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برگشت به پنل اصلی شاپ (از کالبک)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await show_shop_panel(query, user_id)

# ===== بستن پنل =====
async def shop_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن پنل شاپ"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()

