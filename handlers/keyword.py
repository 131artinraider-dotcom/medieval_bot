from telegram import Update
from telegram.ext import ContextTypes
from database import claim_keyword_reward, get_keyword_cooldown, get_user

# ========================================
# کلمات کلیدی مجاز
# ========================================
KEYWORDS = [
    "درود بر لورد",
    "سلام بر لورد",
    "لورد",
]

# ========================================
# پردازش کلمه کلیدی
# ========================================
async def handle_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بررسی و پردازش کلمه کلیدی"""
    
    if not update.message:
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # ===== چک کردن کلمه کلیدی =====
    is_keyword = False
    for keyword in KEYWORDS:
        if keyword in text or text == keyword:
            is_keyword = True
            break
    
    if not is_keyword:
        return
    
    # ===== دریافت جایزه =====
    result = await claim_keyword_reward(user_id)
    
    if not result["success"]:
        if "ثبت‌نام" in result["message"]:
            await update.message.reply_text(
                "❌ شما ثبت‌نام نکردید!\n"
                "برای شروع از /start استفاده کن."
            )
        else:
            # کول‌داون
            remaining = await get_keyword_cooldown(user_id)
            minutes = remaining // 60
            seconds = remaining % 60
            await update.message.reply_text(
                f"⏱️ **صبر کن!**\n\n"
                f"هر ۳ دقیقه فقط یکبار میتونی جایزه بگیری.\n"
                f"زمان باقی‌مونده: {minutes}:{seconds:02d}"
            )
        return
    
    # ===== پیام موفقیت =====
    await update.message.reply_text(
        f"🙏 **درود بر لورد!**\n\n"
        f"💰 **{result['reward']} سکه** بهت هدیه داده شد!\n"
        f"💰 سکه جدید: {result['new_gold']:,}\n\n"
        f"🔄 هر ۳ دقیقه یکبار میتونی این جایزه رو بگیری!"
    )

