from telegram import Update
from telegram.ext import ContextTypes
from database import get_user, get_db

# ========================================
# انتقال پول به کاربر (با ریپلای)
# ========================================
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتقال پول به کاربر با ریپلای"""
    sender_id = update.effective_user.id
    
    # دریافت اطلاعات فرستنده
    sender = await get_user(sender_id)
    if not sender or not sender['is_registered']:
        await update.message.reply_text("❌ شما ثبت‌نام نکردید!")
        return
    
    # چک کردن ریپلای
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ لطفاً به پیام کاربر مورد نظر **ریپلای** کن!\n"
            "مثال: `/pay 1000` (ریپلای به پیام کاربر)\n"
            "یا: `انتقال 1000` (ریپلای به پیام کاربر)"
        )
        return
    
    # دریافت کاربر هدف از ریپلای
    target_user = update.message.reply_to_message.from_user
    
    # جلوگیری از انتقال به خودش
    if sender_id == target_user.id:
        await update.message.reply_text("❌ نمی‌تونی به خودت پول انتقال بدی!")
        return
    
    # دریافت مبلغ
    text = update.message.text.strip()
    
    # پشتیبانی از هر دو فرمت
    if text.startswith("/pay"):
        parts = text.split()
    elif text.startswith("انتقال"):
        parts = text.split()
    else:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n`/pay 1000` یا `انتقال 1000`\n"
            "(با ریپلای به پیام کاربر)",
            parse_mode="Markdown"
        )
        return
    
    if len(parts) < 2:
        await update.message.reply_text("❌ لطفاً مبلغ رو وارد کن! مثال: `/pay 1000`")
        return
    
    try:
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ مبلغ نامعتبر! لطفاً یک عدد وارد کن.")
        return
    
    if amount < 1:
        await update.message.reply_text("❌ حداقل مبلغ برای انتقال **۱ سکه** است!")
        return
    
    # بررسی سکه فرستنده
    if sender['gold'] < amount:
        await update.message.reply_text(
            f"❌ سکه کافی نیست!\n"
            f"💰 سکه‌های تو: {sender['gold']:,}\n"
            f"💰 مبلغ انتقال: {amount:,}"
        )
        return
    
    # بررسی وجود کاربر هدف در دیتابیس
    conn = await get_db()
    target_exists = await conn.fetchval(
        "SELECT user_id FROM users WHERE user_id = $1",
        target_user.id
    )
    
    if not target_exists:
        await conn.close()
        await update.message.reply_text(
            f"❌ کاربر **{target_user.first_name}** در دیتابیس وجود ندارد!\n"
            "احتمالاً ثبت‌نام نکرده."
        )
        return
    
    # ===== انجام انتقال =====
    # کم کردن از فرستنده
    await conn.execute(
        "UPDATE users SET gold = gold - $1 WHERE user_id = $2",
        amount, sender_id
    )
    
    # اضافه کردن به گیرنده
    await conn.execute(
        "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
        amount, target_user.id
    )
    
    # دریافت سکه جدید هر دو
    sender_new_gold = await conn.fetchval(
        "SELECT gold FROM users WHERE user_id = $1",
        sender_id
    )
    
    target_new_gold = await conn.fetchval(
        "SELECT gold FROM users WHERE user_id = $1",
        target_user.id
    )
    
    await conn.close()
    
    # ===== پیام موفقیت =====
    await update.message.reply_text(
        f"✅ **انتقال پول انجام شد!**\n\n"
        f"💰 **{amount:,} سکه** به **{target_user.first_name}** منتقل شد!\n\n"
        f"👤 **{update.effective_user.first_name}:** {sender_new_gold:,} سکه\n"
        f"👤 **{target_user.first_name}:** {target_new_gold:,} سکه",
        parse_mode="Markdown"
    )

