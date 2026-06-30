# handlers/message_logs.py
"""
پنل ادمین برای مشاهده پیام‌های ذخیره‌شده گروه:
- /logs            → مرور صفحه‌به‌صفحه پیام‌های همین گروه
- /logs کلمه       → فیلتر پیام‌هایی که شامل «کلمه» هستن (در همین گروه)
- /chats           → (در پی‌وی) لیست گروه‌هایی که ازشون پیام ذخیره شده
- /logs <chat_id>          → (در پی‌وی) مرور پیام‌های یک گروه خاص با chat_id
- /logs <chat_id> کلمه     → (در پی‌وی) فیلتر پیام‌های یک گروه خاص

دکمه‌های ⬅️ قبلی / بعدی➡️ برای صفحه‌بندی.
"""
from datetime import timedelta
import time
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.admin import is_admin
from database import get_chat_messages_page, search_chat_messages, get_logged_chats, PAGE_SIZE

# تهران از UTC حدوداً ۳:۳۰ جلوتره؛ برای نمایش ساده افست رو هاردکد می‌کنیم
TZ_OFFSET = timedelta(hours=3, minutes=30)

# ذخیره موقت سشن‌های فیلتر/مرور (چون callback_data تلگرام محدود به ۶۴ بایته
# و فیلتر کلمه می‌تونه طولانی باشه، به‌جای گذاشتن خود کلمه تو دکمه، فقط یه
# شناسه کوتاه می‌فرستیم و جزئیات رو این‌جا نگه می‌داریم)
_log_sessions = {}  # session_id -> {"chat_id": int, "keyword": str|None, "ts": float}
_SESSION_TTL = 3600 * 6  # ۶ ساعت


def _make_session(chat_id: int, keyword: str = None) -> str:
    _cleanup_sessions()
    sid = uuid.uuid4().hex[:10]
    _log_sessions[sid] = {"chat_id": chat_id, "keyword": keyword, "ts": time.monotonic()}
    return sid


def _get_session(sid: str):
    s = _log_sessions.get(sid)
    if s:
        s["ts"] = time.monotonic()  # تمدید عمر سشن با هر استفاده
    return s


def _cleanup_sessions():
    if len(_log_sessions) < 200:
        return
    cutoff = time.monotonic() - _SESSION_TTL
    for sid in list(_log_sessions.keys()):
        if _log_sessions[sid]["ts"] < cutoff:
            del _log_sessions[sid]


def _fmt_time(dt):
    if not dt:
        return "-"
    local = dt + TZ_OFFSET
    return local.strftime("%Y-%m-%d %H:%M")


def _build_text(rows, total, page: int, chat_title: str, keyword: str = None):
    total_pages = max(1, -(-total // PAGE_SIZE))  # ceil division

    header = f"📜 **لاگ پیام‌های گروه:** {chat_title or 'نامشخص'}\n"
    if keyword:
        header += f"🔎 فیلتر: «{keyword}»\n"
    header += f"📄 صفحه {page + 1} از {total_pages} — مجموع: {total} پیام\n"
    header += "━━━━━━━━━━━━━━━━━━━━━\n\n"

    if not rows:
        header += "چیزی پیدا نشد."
        return header

    lines = []
    for r in rows:
        name = r["full_name"] or r["username"] or str(r["user_id"])
        uname = f"(@{r['username']})" if r["username"] else ""
        time_str = _fmt_time(r["created_at"])
        text = (r["message_text"] or "").strip()
        if len(text) > 200:
            text = text[:200] + "…"
        lines.append(f"🕒 {time_str} | 👤 {name} {uname}\n💬 {text}\n")

    return header + "\n".join(lines)


def _build_keyboard(chat_id: int, page: int, total: int, keyword: str = None):
    total_pages = max(1, -(-total // PAGE_SIZE))

    sid = _make_session(chat_id, keyword)

    # encode: logs|<session_id>|<page>  (همیشه کوتاه و زیر محدودیت ۶۴ بایت)
    def cb(p):
        return f"logs|{sid}|{p}"

    buttons = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ قبلی", callback_data=cb(page - 1)))
    if page + 1 < total_pages:
        nav_row.append(InlineKeyboardButton("بعدی ➡️", callback_data=cb(page + 1)))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("❌ بستن", callback_data="logs_close")])
    return InlineKeyboardMarkup(buttons)


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کامند /logs - مرور یا فیلتر پیام‌ها"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return

    chat = update.effective_chat
    parts = update.message.text.split(maxsplit=2)
    # parts[0] = /logs

    keyword = None
    target_chat_id = None
    chat_title = None

    if chat.type in ("group", "supergroup"):
        # داخل گروه: /logs  یا  /logs کلمه
        target_chat_id = chat.id
        if len(parts) >= 2:
            keyword = parts[1].strip()
        chat_title = chat.title or ""
    else:
        # داخل پی‌وی: باید chat_id رو بدی -> /logs <chat_id> [کلمه]
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ در پیوی باید آیدی گروه رو بدی!\n"
                "مثال: `/logs -1001234567890`\n"
                "یا: `/logs -1001234567890 سلام`\n\n"
                "برای دیدن لیست گروه‌ها: /chats",
                parse_mode="Markdown"
            )
            return
        try:
            target_chat_id = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ آیدی گروه نامعتبره! باید عدد باشه.")
            return
        if len(parts) >= 3:
            keyword = parts[2].strip()

    page = 0
    if keyword:
        rows, total = await search_chat_messages(target_chat_id, keyword, page)
    else:
        rows, total = await get_chat_messages_page(target_chat_id, page)

    if chat_title is None:
        chat_title = rows[0]["chat_title"] if rows else str(target_chat_id)

    text = _build_text(rows, total, page, chat_title, keyword)
    keyboard = _build_keyboard(target_chat_id, page, total, keyword)

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندل دکمه‌های صفحه‌بندی لاگ پیام‌ها"""
    query = update.callback_query
    user_id = query.from_user.id

    if not await is_admin(user_id):
        await query.answer("❌ شما دسترسی ادمین ندارید!", show_alert=True)
        return

    if query.data == "logs_close":
        await query.answer()
        try:
            await query.delete_message()
        except Exception:
            pass
        return

    # logs|<session_id>|<page>
    try:
        _, sid, page_str = query.data.split("|", 2)
        page = int(page_str)
    except ValueError:
        await query.answer("⚠️ این دکمه منقضی شده، دوباره /logs رو بزن.", show_alert=True)
        return

    session = _get_session(sid)
    if not session:
        await query.answer("⚠️ این دکمه منقضی شده، دوباره /logs رو بزن.", show_alert=True)
        return

    chat_id = session["chat_id"]
    keyword = session["keyword"]

    if keyword:
        rows, total = await search_chat_messages(chat_id, keyword, page)
    else:
        rows, total = await get_chat_messages_page(chat_id, page)

    chat_title = rows[0]["chat_title"] if rows else str(chat_id)
    text = _build_text(rows, total, page, chat_title, keyword)
    keyboard = _build_keyboard(chat_id, page, total, keyword)

    await query.answer()
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception:
        pass


async def chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کامند /chats - لیست گروه‌هایی که ازشون پیام ذخیره شده (برای استفاده در پی‌وی)"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی ادمین ندارید!")
        return

    rows = await get_logged_chats()
    if not rows:
        await update.message.reply_text("هیچ پیامی هنوز ذخیره نشده.")
        return

    lines = ["📋 **گروه‌های دارای لاگ پیام:**\n"]
    for r in rows:
        title = r["chat_title"] or "بدون‌نام"
        lines.append(
            f"• {title}\n"
            f"  `chat_id: {r['chat_id']}` — {r['cnt']} پیام\n"
            f"  آخرین پیام: {_fmt_time(r['last_msg'])}\n"
        )
    lines.append("\nبرای مرور: `/logs <chat_id>`")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
