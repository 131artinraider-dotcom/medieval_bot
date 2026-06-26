import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from config import TOKEN
from database import init_db
from handlers.start import start, handle_name
from handlers.callbacks import button_callback
from handlers.status import status, status_persian
from handlers.inventory import inventory
from handlers.shop import shop, shop_execute_quantity_buy
from handlers.dungeon import dungeon
from handlers.upgrade import upgrade
from handlers.leaderboard import leaderboard
from handlers.duel import duel
from handlers.daily import daily
from handlers.help import help_command
from handlers.keyword import handle_keyword
from handlers.admin import (
    admin_panel,
    admin_add_gold,
    admin_remove_gold,
    admin_reset_player,
    admin_add_exp,
    admin_remove_exp,
    admin_add_upgrade,
    admin_remove_upgrade,
    admin_reset_quests,
    admin_reset_all_quests
)

# ========================================
# تنظیمات لاگ
# ========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========================================
# مقداردهی اولیه دیتابیس
# ========================================
async def post_init(application):
    await init_db()
    print("✅ دیتابیس آماده است!")

# ========================================
# هندلر اصلی پیام‌های متنی (غیر کامند)
# ========================================
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی که کامند نیستند"""
    
    if not update.message:
        return
    
    text = update.message.text.strip()
    
    # ==========================================
    # 1. کلمه کلیدی (در همه جا کار میکنه)
    # ==========================================
    await handle_keyword(update, context)
    
    # ==========================================
    # 2. خرید تعداد مشخص (شاپ) - فقط پیوی
    # ==========================================
    if context.user_data.get('buy_item_name'):
        await shop_execute_quantity_buy(update, context)
        return
    
    # ==========================================
    # 3. مرحله وارد کردن اسم (ثبت‌نام) - فقط پیوی
    # ==========================================
    if context.user_data.get('awaiting_name'):
        if update.effective_chat.type == "private":
            await handle_name(update, context)
        else:
            await update.message.reply_text(
                "❌ لطفاً ثبت‌نام رو در چت خصوصی بات کامل کن."
            )
        return
    
    # ==========================================
    # 4. لغو عملیات (همه جا)
    # ==========================================
    if text == "/cancel":
        if context.user_data.get('buy_item_name'):
            context.user_data.pop('buy_item_name', None)
            await update.message.reply_text("✅ عملیات خرید لغو شد.")
        return
    
    # ==========================================
    # 5. پیام‌های نامعتبر (فقط در چت خصوصی)
    # ==========================================
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "❌ دستور نامعتبر!\n\n"
            "📌 **کامندهای موجود:**\n"
            "/start یا 'شروع' → شروع بازی\n"
            "/status یا 'وضعیت' → مشاهده وضعیت\n"
            "/inventory یا 'اموال' → مشاهده اینونتوری\n"
            "/shop یا 'شاپ' → ورود به فروشگاه\n"
            "/dungeon یا 'دانجن' → ورود به دانجن\n"
            "/upgrade یا 'آپگرید' → آپگرید استت‌ها\n"
            "/leaderboard یا 'لیدربرد' → جدول رتبه‌بندی\n"
            "/duel یا 'دوئل' → دوئل با کاربران گروه\n"
            "/daily یا 'ماموریت' → ماموریت‌های روزانه\n"
            "/help یا 'آموزش' → راهنمای بات\n"
            "/admin → پنل ادمین (فقط ادمین)",
            parse_mode="Markdown"
        )
    # ===== در گروه، پیام‌های معمولی رو نادیده بگیر =====

# ========================================
# تابع اصلی
# ========================================
def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # ==========================================
    # کامندهای انگلیسی (همه جا کار میکنن)
    # ==========================================
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("inventory", inventory))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("dungeon", dungeon))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("duel", duel))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("help", help_command))
    
    # ==========================================
    # کامندهای فارسی (همه جا کار میکنن)
    # ==========================================
    app.add_handler(CommandHandler("شروع", start))
    app.add_handler(CommandHandler("وضعیت", status_persian))
    app.add_handler(CommandHandler("اموال", inventory))
    app.add_handler(CommandHandler("شاپ", shop))
    app.add_handler(CommandHandler("دانجن", dungeon))
    app.add_handler(CommandHandler("آپگرید", upgrade))
    app.add_handler(CommandHandler("لیدربرد", leaderboard))
    app.add_handler(CommandHandler("رنکینگ", leaderboard))
    app.add_handler(CommandHandler("دوئل", duel))
    app.add_handler(CommandHandler("ماموریت", daily))
    app.add_handler(CommandHandler("روزانه", daily))
    app.add_handler(CommandHandler("آموزش", help_command))
    app.add_handler(CommandHandler("راهنما", help_command))
    
    # ==========================================
    # کامندهای ادمین (انگلیسی)
    # ==========================================
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addgold", admin_add_gold))
    app.add_handler(CommandHandler("removegold", admin_remove_gold))
    app.add_handler(CommandHandler("reset", admin_reset_player))
    app.add_handler(CommandHandler("addexp", admin_add_exp))
    app.add_handler(CommandHandler("removeexp", admin_remove_exp))
    app.add_handler(CommandHandler("addupgrade", admin_add_upgrade))
    app.add_handler(CommandHandler("removeupgrade", admin_remove_upgrade))
    app.add_handler(CommandHandler("resetquests", admin_reset_quests))
    app.add_handler(CommandHandler("resetallquests", admin_reset_all_quests))
    
    # ==========================================
    # کامندهای ادمین (فارسی)
    # ==========================================
    app.add_handler(CommandHandler("ادمین", admin_panel))
    app.add_handler(CommandHandler("اضافه_سکه", admin_add_gold))
    app.add_handler(CommandHandler("کم_سکه", admin_remove_gold))
    app.add_handler(CommandHandler("ریست", admin_reset_player))
    app.add_handler(CommandHandler("اضافه_اکسپی", admin_add_exp))
    app.add_handler(CommandHandler("کم_اکسپی", admin_remove_exp))
    app.add_handler(CommandHandler("اضافه_آپگرید", admin_add_upgrade))
    app.add_handler(CommandHandler("کم_آپگرید", admin_remove_upgrade))
    
    # ==========================================
    # هندلر پیام‌های متنی (غیر کامند)
    # ==========================================
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_messages
        )
    )
    
    # ==========================================
    # هندلر دکمه‌ها (کالبک)
    # ==========================================
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # ==========================================
    # راه‌اندازی
    # ==========================================
    print("=" * 50)
    print("⚔️ بات قرون وسطایی با تمام قابلیت‌ها روشن شد! 🏰")
    print("=" * 50)
    print("📌 کامندهای عمومی (انگلیسی و فارسی):")
    print("   /start یا 'شروع' → شروع بازی")
    print("   /status یا 'وضعیت' → مشاهده وضعیت")
    print("   /inventory یا 'اموال' → مشاهده اینونتوری")
    print("   /shop یا 'شاپ' → ورود به فروشگاه")
    print("   /dungeon یا 'دانجن' → ورود به دانجن")
    print("   /upgrade یا 'آپگرید' → آپگرید استت‌ها")
    print("   /leaderboard یا 'لیدربرد' → جدول رتبه‌بندی")
    print("   /duel یا 'دوئل' → دوئل با کاربران گروه")
    print("   /daily یا 'ماموریت' → ماموریت‌های روزانه")
    print("   /help یا 'آموزش' → راهنمای بات")
    print("   'درود بر لورد' → جایزه ۱۰۰-۱۵۰ سکه (هر ۳ دقیقه)")
    print("")
    print("👑 کامندهای ادمین (با ریپلای):")
    print("   /admin یا 'ادمین' → راهنمای پنل ادمین")
    print("   /addgold یا 'اضافه_سکه' → اضافه کردن سکه")
    print("   /removegold یا 'کم_سکه' → کم کردن سکه")
    print("   /addexp یا 'اضافه_اکسپی' → اضافه کردن اکس‌پی")
    print("   /removeexp یا 'کم_اکسپی' → کم کردن اکس‌پی")
    print("   /addupgrade یا 'اضافه_آپگرید' → اضافه کردن آپگرید پوینت")
    print("   /removeupgrade یا 'کم_آپگرید' → کم کردن آپگرید پوینت")
    print("   /resetquests → ریست کوئست‌های یه کاربر")
    print("   /resetallquests → ریست همه کوئست‌ها")
    print("   /reset یا 'ریست' → ریست کامل کاربر")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()

