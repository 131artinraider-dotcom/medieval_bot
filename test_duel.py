from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random

TOKEN = "8997021672:AAG_U864cuKDWVA0tK7O6yoNpY2VS_zragE"

active_duels = {}

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ دوئل فقط در گروه‌ها!") 
        return
    
    # دریافت مبلغ
    parts = update.message.text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ مبلغ رو وارد کن! مثال: /duel 500")
        return
    
    try:
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ عدد معتبر وارد کن!")
        return
    
    if amount < 100:
        await update.message.reply_text("❌ حداقل ۱۰۰ سکه!")
        return
    
    duel_key = f"duel_{chat_id}"
    if duel_key in active_duels:
        await update.message.reply_text("⚠️ یک دوئل فعال هست!")
        return
    
    active_duels[duel_key] = {
        "creator_id": user_id,
        "amount": amount,
        "accepted": False
    }
    
    keyboard = [[InlineKeyboardButton("⚔️ قبول دوئل", callback_data="duel_accept")]]
    
    await update.message.reply_text(
        f"⚔️ دوئل! مبلغ: {amount} سکه",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def duel_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("✅ دکمه دوئل کلیک شد!")  # این باید توی ترمینال چاپ بشه
    
    query = update.callback_query
    await query.answer("قبول شد!", show_alert=True)
    
    await query.edit_message_text("✅ دوئل قبول شد! (تست)")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("duel", duel))
    app.add_handler(CallbackQueryHandler(duel_accept))
    
    print("🚀 بات تست دوئل روشن شد!")
    app.run_polling()

if __name__ == "__main__":
    main()

