import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3, re
from datetime import datetime, timedelta

BOT_TOKEN = "8389345826:AAH2yz5RrvOwvtQoW2ROG9E3-_ti7lKekMg"
OWNER_ID = 8286004637
MAX_WARNINGS = 4
AUTO_MUTE_SECONDS = 24 * 60 * 60

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, chat_id INTEGER, count INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS appeals (user_id INTEGER, grp TEXT, reason TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS reports (reporter INTEGER, target INTEGER, username TEXT, proof TEXT)")
db.commit()

user_state = {}

# ---------- HELPERS ----------
def is_admin(chat_id, user_id):
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ["administrator", "creator"]
    except:
        return False

def has_link(text):
    return bool(re.search(r"(https?://|t\.me/)", text or ""))

# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(message):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("CHAT GC", callback_data="appeal_CHAT_GC"),
        InlineKeyboardButton("Buy & Sell", callback_data="appeal_BUY_SELL")
    )
    bot.send_message(
        message.chat.id,
        "Welcome! Choose a group to start your appeal.",
        reply_markup=kb
    )

# ---------- CANCEL ----------
@bot.message_handler(commands=["cancel"])
def cancel_cmd(message):
    user_state.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "Appeal canceled.")

@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel_btn(call):
    user_state.pop(call.from_user.id, None)
    bot.send_message(call.message.chat.id, "Appeal canceled.")

# ---------- APPEAL GROUP ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("appeal_"))
def appeal_group(call):
    grp = call.data.replace("appeal_", "")
    user_state[call.from_user.id] = {"type": "appeal", "group": grp}

    bot.send_message(call.message.chat.id, "You are not muted or banned.")

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel"))

    bot.send_message(
        call.message.chat.id,
        "Share your appeal reason.",
        reply_markup=kb
    )

# ---------- SAVE APPEAL ----------
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("type") == "appeal")
def save_appeal(message):
    if message.text.lower().startswith("cancel"):
        user_state.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "Appeal canceled.")
        return

    data = user_state.pop(message.from_user.id)
    grp = data["group"]

    cur.execute("INSERT INTO appeals VALUES (?,?,?)", (message.from_user.id, grp, message.text))
    db.commit()

    bot.send_message(message.chat.id, "✅ Appeal submitted.")

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Approve (Unmute)", callback_data=f"accept_{message.from_user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{message.from_user.id}")
    )

    bot.send_message(
        OWNER_ID,
        f"📢 <b>NEW APPEAL</b>\n"
        f"👤 {message.from_user.first_name}\n"
        f"🆔 {message.from_user.id}\n"
        f"📍 Group: {grp}\n"
        f"📝 {message.text}",
        reply_markup=kb
    )

# ---------- APPEAL ACTION ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("accept_"))
def accept(call):
    if call.from_user.id != OWNER_ID:
        return
    uid = int(call.data.split("_")[1])
    try:
        bot.restrict_chat_member(call.message.chat.id, uid, can_send_messages=True)
    except:
        pass
    bot.send_message(call.message.chat.id, "✅ Appeal approved. User unmuted.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
