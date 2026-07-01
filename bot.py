import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.error import TimedOut, NetworkError

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
    admin_panel, admin_add_gold, admin_remove_gold, admin_reset_player,
    admin_add_exp, admin_remove_exp, admin_add_upgrade, admin_remove_upgrade,
    admin_reset_quests, admin_reset_all_quests, admin_rename_player,
    admin_close_all_panels,
    admin_reset_dungeon
)
from handlers.logger import log_group_message
from handlers.message_logs import logs_command, chats_command

# ========================================
# تنظیمات لاگ - فقط WARNING و بالاتر
# ========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
# httpx رو کاملاً ساکت کن
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

async def post_init(application):
    await init_db()
    print("✅ دیتابیس آماده است!")

# ========================================
# پاک‌سازی پنل‌های منقضی (هر ۱۰ دقیقه)
# ========================================
async def cleanup_expired_panels(context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن و دیلیت پنل‌های بیش از ۱۰ دقیقه"""
    import time
    from database import end_dungeon
    now = time.time()
    expired = [
        (k, v) for k, v in list(context.bot_data.items())
        if k.startswith("panel_") and isinstance(v, dict) and now - v.get("ts", now) > 5
    ]
    for k, v in expired:
        try:
            chat_id = v.get("chat_id")
            message_id = int(k.replace("panel_", ""))
            if chat_id:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
        # اگه پنل نبرد دانجن بود، دانجن رو کاملاً از دیتابیس DELETE کن
        if v.get("type") == "dungeon_active":
            try:
                user_id = v.get("uid")
                if user_id:
                    from database import get_db
                    conn = await get_db()
                    await conn.execute("DELETE FROM dungeons WHERE user_id = $1 AND is_active = TRUE", user_id)
                    await conn.close()
                    print(f"[CLEANUP] Deleted dungeon for user {user_id}")
            except Exception as e:
                print(f"[CLEANUP ERROR] {e}")
        context.bot_data.pop(k, None)

# ========================================
# هندلر اصلی پیام‌های متنی
# ========================================
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = update.message.text.strip()

    # ===== ذخیره همه پیام‌های گروه (قبل از هر پردازشی) =====
    await log_group_message(update, context)

    if text.startswith("/logs"):
        await logs_command(update, context); return
    if text.startswith("/chats"):
        await chats_command(update, context); return

    if text.startswith("/addgold"):
        await admin_add_gold(update, context); return
    if text.startswith("/removegold"):
        await admin_remove_gold(update, context); return
    if text.startswith("/resetallquests"):
        await admin_reset_all_quests(update, context); return
    if text.startswith("/resetquests"):
        await admin_reset_quests(update, context); return
    if text.startswith("/resetdungeon"):
        await admin_reset_dungeon(update, context); return
    if text.startswith("/reset"):
        await admin_reset_player(update, context); return
    if text.startswith("/addexp"):
        await admin_add_exp(update, context); return
    if text.startswith("/removeexp"):
        await admin_remove_exp(update, context); return
    if text.startswith("/addupgrade"):
        await admin_add_upgrade(update, context); return
    if text.startswith("/removeupgrade"):
        await admin_remove_upgrade(update, context); return
    if text.startswith("/rename"):
        await admin_rename_player(update, context); return
    if text == "/admin":
        await admin_panel(update, context); return
    if text == "/closeallpanels":
        await admin_close_all_panels(update, context); return

    if text.startswith("/start"):
        await start(update, context); return
    if text.startswith("/status"):
        await status(update, context); return
    if text.startswith("/inventory"):
        await inventory(update, context); return
    if text.startswith("/shop"):
        await shop(update, context); return
    if text.startswith("/dungeon"):
        await dungeon(update, context); return
    if text.startswith("/upgrade"):
        await upgrade(update, context); return
    if text.startswith("/leaderboard"):
        await leaderboard(update, context); return
    if text.startswith("/duel"):
        await duel(update, context); return
    if text.startswith("/daily"):
        await daily(update, context); return
    if text.startswith("/pay"):
        await pay(update, context); return
    if text.startswith("/help"):
        await help_command(update, context); return

    if text == "شروع":
        await start(update, context); return
    if text == "وضعیت":
        await status_persian(update, context); return
    if text == "اموال":
        await inventory(update, context); return
    if text == "شاپ":
        await shop(update, context); return
    if text == "دانجن":
        await dungeon(update, context); return
    if text == "آپگرید":
        await upgrade(update, context); return
    if text in ["لیدربرد", "رنکینگ"]:
        await leaderboard(update, context); return
    if text.startswith("دوئل"):
        await duel(update, context); return
    if text in ["ماموریت", "روزانه"]:
        await daily(update, context); return
    if text.startswith("انتقال"):
        await pay(update, context); return
    if text in ["آموزش", "راهنما"]:
        await help_command(update, context); return

    if context.user_data.get('buy_item_name'):
        await shop_execute_quantity_buy(update, context); return

    if context.user_data.get('awaiting_name'):
        await handle_name(update, context)
        return

    if text == "/cancel":
        if context.user_data.get('buy_item_name'):
            context.user_data.pop('buy_item_name', None)
            await update.message.reply_text("✅ عملیات خرید لغو شد.")
        return

    await handle_keyword(update, context)

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
            "/pay یا 'انتقال' → انتقال پول\n"
            "/help یا 'آموزش' → راهنمای بات\n"
            "/admin → پنل ادمین (فقط ادمین)",
            parse_mode="Markdown"
        )

# ========================================
# هندلر خطاها
# ========================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    if isinstance(error, (TimedOut, NetworkError)):
        return
    logging.error(f"خطا: {error}", exc_info=context.error)
    if update and hasattr(update, 'callback_query') and update.callback_query:
        try:
            await update.callback_query.answer("❌ خطایی پیش اومد! دوباره تلاش کن.", show_alert=True)
        except Exception:
            pass

# ========================================
# تابع اصلی
# ========================================
def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(MessageHandler(filters.TEXT, handle_text_messages))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)

    # پاک‌سازی پنل‌های منقضی هر ۱۰ دقیقه
    app.job_queue.run_repeating(cleanup_expired_panels, interval=5, first=5)

    print("⚔️ بات قرون وسطایی روشن شد! 🏰")
    app.run_polling()

if __name__ == "__main__":
    main()
