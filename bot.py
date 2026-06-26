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
# هندلر اصلی پیام‌های متنی
# ========================================
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی که کامند نیستند"""
    
    if not update.message:
        return
    
    text = update.message.text.strip()
    
    # ==========================================
    # کلمه کلیدی (درود بر لورد) - اول از همه
    # ==========================================
    await handle_keyword(update, context)
    
    # ==========================================
    # خرید تعداد مشخص (شاپ)
    # ==========================================
    if context.user_data.get('buy_item_name'):
        await shop_execute_quantity_buy(update, context)
        return
    
    # ==========================================
    # کامندهای ادمین (با ریپلای)
    # ==========================================
    if text.startswith("/addgold"):
        await admin_add_gold(update, context)
        return
    
    if text.startswith("/removegold"):
        await admin_remove_gold(update, context)
        return
    
    if text.startswith("/reset"):
        await admin_reset_player(update, context)
        return
    
    if text.startswith("/addexp"):
        await admin_add_exp(update, context)
        return
    
    if text.startswith("/removeexp"):
        await admin_remove_exp(update, context)
        return
    
    if text.startswith("/addupgrade"):
        await admin_add_upgrade(update, context)
        return
    
    if text.startswith("/removeupgrade"):
        await admin_remove_upgrade(update, context)
        return
    
    if text == "/admin":
        await admin_panel(update, context)
        return
    
    if text.startswith("/resetquests"):
        await admin_reset_quests(update, context)
        return
    
    if text.startswith("/resetallquests"):
        await admin_reset_all_quests(update, context)
        return
    
    # ==========================================
    # دوئل (با مبلغ)
    # ==========================================
    if text.startswith("/duel"):
        await duel(update, context)
        return
    
    if text.startswith("دوئل"):
        await duel(update, context)
        return
    
    # ==========================================
    # کامندهای فارسی
    # ==========================================
    if text == "شروع":
        await start(update, context)
        return
    
    if text == "وضعیت":
        await status_persian(update, context)
        return
    
    if text == "اموال":
        await inventory(update, context)
        return
    
    if text == "شاپ":
        await shop(update, context)
        return
    
    if text == "دانجن":
        await dungeon(update, context)
        return
    
    if text == "آپگرید":
        await upgrade(update, context)
        return
    
    if text == "لیدربرد" or text == "رنکینگ":
        await leaderboard(update, context)
        return
    
    if text == "ماموریت" or text == "روزانه":
        await daily(update, context)
        return
    
    if text == "/help" or text == "آموزش" or text == "راهنما":
        await help_command(update, context)
        return
    
    # ==========================================
    # مرحله وارد کردن اسم (ثبت‌نام)
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
    # لغو عملیات
    # ==========================================
    if text == "/cancel":
        if context.user_data.get('buy_item_name'):
            context.user_data.pop('buy_item_name', None)
            await update.message.reply_text("✅ عملیات خرید لغو شد.")
        return
    
    # ==========================================
    # پیام‌های نامعتبر (فقط در چت خصوصی)
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
            "/duel یا 'دوئل 500' → دوئل با کاربران گروه\n"
            "/daily یا 'ماموریت' → ماموریت‌های روزانه\n"
            "/help یا 'آموزش' → راهنمای بات\n"
            "/admin → پنل ادمین (فقط ادمین)",
            parse_mode="Markdown"
        )

# ========================================
# تابع اصلی
# ========================================
def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # ==========================================
    # کامندهای عمومی
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
    # کامندهای ادمین
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
    # هندلر پیام‌های متنی (بدون /)
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
    print("📌 کامندهای عمومی:")
    print("   /start یا 'شروع' → شروع بازی")
    print("   /status یا 'وضعیت' → مشاهده وضعیت")
    print("   /inventory یا 'اموال' → مشاهده اینونتوری")
    print("   /shop یا 'شاپ' → ورود به فروشگاه")
    print("   /dungeon یا 'دانجن' → ورود به دانجن")
    print("   /upgrade یا 'آپگرید' → آپگرید استت‌ها")
    print("   /leaderboard یا 'لیدربرد' → جدول رتبه‌بندی")
    print("   /duel یا 'دوئل 500' → دوئل با کاربران گروه")
    print("   /daily یا 'ماموریت' → ماموریت‌های روزانه")
    print("   /help یا 'آموزش' → راهنمای بات")
    print("   'درود بر لورد' → جایزه ۱۰۰-۱۵۰ سکه (هر ۳ دقیقه)")
    print("")
    print("👑 کامندهای ادمین (با ریپلای به پیام کاربر):")
    print("   /admin → راهنمای پنل ادمین")
    print("   /addgold 1000 → اضافه کردن سکه")
    print("   /removegold 500 → کم کردن سکه")
    print("   /addexp 100 → اضافه کردن اکس‌پی")
    print("   /removeexp 50 → کم کردن اکس‌پی")
    print("   /addupgrade 5 → اضافه کردن آپگرید پوینت")
    print("   /removeupgrade 3 → کم کردن آپگرید پوینت")
    print("   /resetquests → ریست کوئست‌های یه کاربر (ریپلای)")
    print("   /resetallquests → ریست همه کوئست‌ها")
    print("   /reset → ریست کامل کاربر")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()

