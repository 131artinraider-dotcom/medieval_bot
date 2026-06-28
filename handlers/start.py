from telegram import Update
from telegram.ext import ContextTypes
from database import create_user, is_user_registered, register_character, add_item, equip_item, update_user_stats
from utils.keyboards import class_selection_keyboard
from config import CLASSES, MIN_NAME_LENGTH, MAX_NAME_LENGTH, INITIAL_ITEMS

# ========================================
# کامند /start
# ========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /start - مرحله ثبت‌نام"""
    user = update.effective_user
    user_id = user.id
    
    # ثبت اولیه کاربر
    await create_user(user_id, user.username)
    
    # چک کردن ثبت‌نام
    is_registered = await is_user_registered(user_id)
    
    if is_registered:
        await update.message.reply_text(
            f"✅ شما قبلاً شخصیت خودت رو ساختی {user.first_name}! 🏰\n"
            "برای مشاهده وضعیت از /status یا 'وضعیت' استفاده کن.\n"
            "برای راهنمای کامل از /help یا 'آموزش' استفاده کن.",
            parse_mode="Markdown"
        )
        return
    
    # مرحله وارد کردن اسم
    context.user_data['awaiting_name'] = True
    await update.message.reply_text(
        "🏰 **به دنیای قرون وسطی خوش آمدی!**\n\n"
        "برای شروع ماجراجویی، ابتدا باید شخصیت خودت رو بسازی.\n"
        f"لطفاً **اسم شخصیت** خودت رو وارد کن ({MIN_NAME_LENGTH} تا {MAX_NAME_LENGTH} کاراکتر):",
        parse_mode="Markdown"
    )

# ========================================
# دریافت اسم شخصیت
# ========================================
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت اسم و نمایش کلاس‌ها"""
    if not context.user_data.get('awaiting_name'):
        return
    
    name = update.message.text.strip()
    
    # اعتبارسنجی اسم
    if len(name) < MIN_NAME_LENGTH or len(name) > MAX_NAME_LENGTH:
        await update.message.reply_text(
            f"❌ اسم باید بین {MIN_NAME_LENGTH} تا {MAX_NAME_LENGTH} کاراکتر باشه. دوباره وارد کن:"
        )
        return
    
    # ذخیره اسم موقت
    context.user_data['character_name'] = name
    context.user_data['awaiting_name'] = False
    
    # توضیحات کلاس‌ها
    class_descs = "\n".join([
        f"🔹 {cls['emoji']} **{cls['name']}**: {cls['desc']}"
        for cls in CLASSES.values()
    ])
    
    await update.message.reply_text(
        f"⚔️ **انتخاب کلاس**\n\n"
        f"شخصیتت با اسم **{name}** ساخته میشه.\n"
        f"یکی از کلاس‌های زیر رو انتخاب کن:\n\n{class_descs}",
        reply_markup=class_selection_keyboard(),
        parse_mode="Markdown"
    )

# ========================================
# انتخاب کلاس
# ========================================
async def select_class_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثبت کلاس انتخاب شده و تکمیل ثبت‌نام"""
    query = update.callback_query
    user_id = query.from_user.id

    # چک مالکیت پنل - فقط کسی که /start زده میتونه کلاس انتخاب کنه
    if not context.user_data.get('character_name'):
        await query.answer("❌ این پنل مال تو نیست!", show_alert=True)
        return

    await query.answer()
    
    data = query.data
    
    if data == "cancel_registration":
        await query.edit_message_text("❌ ثبت‌نام لغو شد. برای شروع دوباره /start رو بزن.")
        context.user_data.clear()
        return
    
    class_key = data.replace("class_", "")
    if class_key not in CLASSES:
        await query.edit_message_text("❌ کلاس نامعتبر!")
        return
    
    cls = CLASSES[class_key]
    user = query.from_user
    name = context.user_data.get('character_name', 'ماجراجو')
    
    # ===== ثبت کلاس در دیتابیس =====
    start_exp = cls.get('start_exp', 0)
    await register_character(
        user.id,
        name,
        class_key,
        {
            'hp': cls['hp'],
            'atk': cls['atk'],
            'def': cls['def'],
            'spd': cls['spd'],
            'lck': cls['lck']
        },
        start_exp
    )
    
    # ===== اضافه کردن آیتم‌های اولیه =====
    initial_items = INITIAL_ITEMS.get(class_key, {})
    
    # سلاح‌ها
    for weapon_name, qty in initial_items.get('weapons', []):
        await add_item(user.id, 'weapon', weapon_name, qty)
        await equip_item(user.id, 'weapon', weapon_name)
    
    # زره‌ها
    for armor_name, qty in initial_items.get('armors', []):
        await add_item(user.id, 'armor', armor_name, qty)
        await equip_item(user.id, 'armor', armor_name)
    
    # آیتم‌های مصرفی
    for consumable_name, qty in initial_items.get('consumables', []):
        level = 1
        if "لول" in consumable_name:
            try:
                level = int(consumable_name.split("لول")[-1].strip())
            except:
                level = 1
        await add_item(user.id, 'consumable', consumable_name, qty, level)
    
    # برای سامورایی که از لول ۳ شروع میکنه، سطح رو آپدیت کن
    if class_key == "samurai":
        await update_user_stats(user.id, level=3, exp=200)
    
    context.user_data.clear()
    
    # ===== پیام تایید نهایی با راهنمای سریع =====
    await query.edit_message_text(
        f"✅ **شخصیت تو ساخته شد!**\n\n"
        f"👤 اسم: {name}\n"
        f"📖 کلاس: {cls['emoji']} {cls['name']}\n\n"
        f"📊 **استت‌های تو:**\n"
        f"❤️ جون: {cls['hp']}\n"
        f"⚔️ قدرت اتک: {cls['atk']}\n"
        f"🛡️ قدرت دفاع: {cls['def']}\n"
        f"💨 سرعت: {cls['spd']}\n"
        f"🍀 شانس: {cls['lck']}\n\n"
        f"🎒 **آیتم‌های اولیه به اینونتوری اضافه شد!**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **راهنمای سریع:**\n"
        f"• برای مشاهده وضعیت: /status یا 'وضعیت'\n"
        f"• برای مشاهده اینونتوری: /inventory یا 'اموال'\n"
        f"• برای ورود به فروشگاه: /shop یا 'شاپ'\n"
        f"• برای ماجراجویی: /dungeon یا 'دانجن'\n"
        f"• برای راهنمای کامل: /help یا 'آموزش'\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 **کانال ما:** @arfamilyy1\n"
        f"🎮 حالا ماجراجوییت رو شروع کن! 🏰",
        parse_mode="Markdown"
    )
