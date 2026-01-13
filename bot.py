import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import re
from datetime import datetime, timedelta

BOT_TOKEN = "8389345826:AAH2yz5RrvOwvtQoW2ROG9E3-_ti7lKekMg"
OWNER_ID = 8286004637

AUTO_MUTE_SECONDS = 24 * 60 * 60  # 24 hours
MAX_WARNINGS = 4

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# ================= DATABASE =================
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS appeals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    appeal_type TEXT,
    reason TEXT,
    status TEXT,
    time TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    user_id INTEGER PRIMARY KEY,
    count INTEGER
)
""")

db.commit()

# ================= UTIL =================
def is_link(text):
    return bool(re.search(r"(http|https|t\.me)", text.lower()))

# ================= APPEAL =================
@bot.message_handler(commands=["appeal"])
def appeal_start(message):
    kb = InlineKeyboardMarkup()
    for t in ["Muted", "Warned", "Banned", "Other"]:
        kb.add(InlineKeyboardButton(t, callback_data=f"appeal:{t}"))
    bot.send_message(message.chat.id, "Choose appeal type:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("appeal:"))
def appeal_type(call):
    appeal_type = call.data.split(":")[1]
    bot.send_message(call.message.chat.id, "Send appeal reason:")
    bot.register_next_step_handler(call.message, save_appeal, appeal_type)

def save_appeal(message, appeal_type):
    cur.execute(
        "INSERT INTO appeals VALUES (NULL,?,?,?,?,?,?)",
        (
            message.from_user.id,
            message.from_user.username,
            appeal_type,
            message.text,
            "Pending",
            datetime.now().strftime("%d-%m-%Y %H:%M")
        )
    )
    db.commit()
    appeal_id = cur.lastrowid

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{appeal_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject:{appeal_id}")
    )

    bot.send_message(
        OWNER_ID,
        f"📩 NEW APPEAL\n\n"
        f"ID: {appeal_id}\n"
        f"User: @{message.from_user.username}\n"
        f"User ID: {message.from_user.id}\n"
        f"Type: {appeal_type}\n\n"
        f"Reason:\n{message.text}",
        reply_markup=kb
    )

    bot.send_message(message.chat.id, "✅ Appeal submitted. Please wait.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("approve:"))
def approve(call):
    appeal_id = int(call.data.split(":")[1])
    cur.execute("SELECT user_id, appeal_type FROM appeals WHERE id=?", (appeal_id,))
    row = cur.fetchone()

    if not row:
        return

    user_id, appeal_type = row

    if appeal_type == "Muted":
        try:
            bot.restrict_chat_member(call.message.chat.id, user_id, until_date=0, can_send_messages=True)
        except:
            pass

    cur.execute("UPDATE appeals SET status='Approved' WHERE id=?", (appeal_id,))
    db.commit()

    bot.send_message(user_id, "✅ Your appeal has been APPROVED.")
    bot.edit_message_text(f"✅ Appeal {appeal_id} approved.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject:"))
def reject(call):
    appeal_id = int(call.data.split(":")[1])
    cur.execute("SELECT user_id FROM appeals WHERE id=?", (appeal_id,))
    row = cur.fetchone()

    if not row:
        return

    user_id = row[0]
    cur.execute("UPDATE appeals SET status='Rejected' WHERE id=?", (appeal_id,))
    db.commit()

    bot.send_message(user_id, "❌ Your appeal has been REJECTED.")
    bot.edit_message_text(f"❌ Appeal {appeal_id} rejected.", call.message.chat.id, call.message.message_id)

# ================= REPORT SYSTEM =================
@bot.message_handler(commands=["report"])
def report(message):
    if not message.reply_to_message:
        bot.reply_to(message, "Reply to the message you want to report.")
        return

    offender = message.reply_to_message.from_user
    bot.forward_message(OWNER_ID, message.chat.id, message.reply_to_message.message_id)

    bot.send_message(
        OWNER_ID,
        f"🚨 MESSAGE REPORTED\n\n"
        f"Group: {message.chat.title}\n"
        f"Offender: @{offender.username}\n"
        f"User ID: {offender.id}\n"
        f"Reported by: @{message.from_user.username}"
    )

    bot.reply_to(message, "✅ Report sent to admin.")

# ================= LINK WARNING =================
@bot.message_handler(func=lambda m: m.chat.type in ["group", "supergroup"] and is_link(m.text or ""))
def warn_link(message):
    user_id = message.from_user.id

    cur.execute("SELECT count FROM warnings WHERE user_id=?", (user_id,))
    row = cur.fetchone()

    count = row[0] + 1 if row else 1

    cur.execute("REPLACE INTO warnings VALUES (?,?)", (user_id, count))
    db.commit()

    if count >= MAX_WARNINGS:
        try:
            bot.restrict_chat_member(
                message.chat.id,
                user_id,
                until_date=datetime.now() + timedelta(seconds=AUTO_MUTE_SECONDS),
                can_send_messages=False
            )
        except:
            pass

        bot.reply_to(message, "🔇 You have been muted for 24 hours (4 warnings).")
    else:
        bot.reply_to(message, f"⚠️ Warning {count}/{MAX_WARNINGS}: Links are not allowed.")

bot.infinity_polling()
