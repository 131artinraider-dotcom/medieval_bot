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
from handlers.pay import pay
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
    """مدیریت همه پیام‌های متنی (کامندهای انگلیسی و فارسی)"""
    
    if not update.message:
        return
    
    text = update.message.text.strip()
    
    # ==========================================
    # 1. کامندهای ادمین (با ریپلای)
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
    # 2. کامندهای انگلیسی (با /)
    # ==========================================
    if text.startswith("/start"):
        await start(update, context)
        return
    
    if text.startswith("/status"):
        await status(update, context)
        return
    
    if text.startswith("/inventory"):
        await inventory(update, context)
        return
    
    if text.startswith("/shop"):
        await shop(update, context)
        return
    
    if text.startswith("/dungeon"):
        await dungeon(update, context)
        return
    
    if text.startswith("/upgrade"):
        await upgrade(update, context)
        return
    
    if text.startswith("/leaderboard"):
        await leaderboard(update, context)
        return
    
    if text.startswith("/duel"):
        await duel(update, context)
        return
    
    if text.startswith("/daily"):
        await daily(update, context)
        return
    
    if text.startswith("/pay"):
        await pay(update, context)
        return
    
    if text.startswith("/help"):
        await help_command(update, context)
        return
    
    # ==========================================
    # 3. کامندهای فارسی (بدون /)
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
    
    if text.startswith("دوئل"):
        await duel(update, context)
        return
    
    if text == "ماموریت" or text == "روزانه":
        await daily(update, context)
        return
    
    if text.startswith("انتقال"):
        await pay(update, context)
        return
    
    if text == "آموزش" or text == "راهنما":
        await help_command(update, context)
        return
    
    # ==========================================
    # 4. کلمه کلیدی (درود بر لورد)
    # ==========================================
    await handle_keyword(update, context)
    
    # ==========================================
    # 5. خرید تعداد مشخص (شاپ) - فقط پیوی
    # ==========================================
    if context.user_data.get('buy_item_name'):
        await shop_execute_quantity_buy(update, context)
        return
    
    # ==========================================
    # 6. مرحله وارد کردن اسم (ثبت‌نام) - فقط پیوی
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
    # 7. لغو عملیات
    # ==========================================
    if text == "/cancel":
        if context.user_data.get('buy_item_name'):
            context.user_data.pop('buy_item_name', None)
            await update.message.reply_text("✅ عملیات خرید لغو شد.")
        return
    
    # ==========================================
    # 8. پیام‌های نامعتبر (فقط در چت خصوصی)
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
            "/pay یا 'انتقال' → انتقال پول به کاربر (ریپلای)\n"
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
    # هندلر پیام‌های متنی (همه پیام‌ها)
    # ==========================================
    app.add_handler(
        MessageHandler(
            filters.TEXT,
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
    print("📌 کامندهای انگلیسی (با /):")
    print("   /start, /status, /inventory, /shop, /dungeon")
    print("   /upgrade, /leaderboard, /duel, /daily, /pay, /help")
    print("")
    print("📌 کامندهای فارسی (بدون /):")
    print("   شروع, وضعیت, اموال, شاپ, دانجن")
    print("   آپگرید, لیدربرد, رنکینگ, دوئل, ماموریت")
    print("   روزانه, انتقال, آموزش, راهنما")
    print("")
    print("📌 کلمه کلیدی:")
    print("   'درود بر لورد' → جایزه ۱۰۰-۱۵۰ سکه (هر ۳ دقیقه)")
    print("")
    print("👑 کامندهای ادمین (با ریپلای):")
    print("   /admin → راهنما")
    print("   /addgold, /removegold → مدیریت سکه")
    print("   /addexp, /removeexp → مدیریت اکس‌پی")
    print("   /addupgrade, /removeupgrade → مدیریت آپگرید")
    print("   /resetquests, /resetallquests → مدیریت کوئست")
    print("   /reset → ریست کامل کاربر")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()

