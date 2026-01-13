import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from datetime import datetime, timedelta
import re

BOT_TOKEN = "8389345826:AAH2yz5RrvOwvtQoW2ROG9E3-_ti7lKekMg"
OWNER_ID = 8286004637
MAX_WARNINGS = 4
AUTO_MUTE_SECONDS = 24 * 60 * 60

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, chat_id INTEGER, count INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS appeals (user_id INTEGER, group_name TEXT, reason TEXT, time TEXT)")
db.commit()

# ---------- HELPERS ----------

def is_admin(chat_id, user_id):
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ["administrator", "creator"]
    except:
        return False

def has_link(text):
    return bool(re.search(r"(https?://|t\.me/|telegram\.me/)", text or ""))

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

# ---------- CANCEL COMMAND ----------

@bot.message_handler(commands=["cancel"])
def cancel_cmd(message):
    bot.send_message(message.chat.id, "❌ Appeal canceled.")

# ---------- APPEAL FLOW ----------

@bot.callback_query_handler(func=lambda c: c.data.startswith("appeal_"))
def appeal_group(call):
    group = call.data.replace("appeal_", "")

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel_appeal"))

    msg = bot.send_message(
        call.message.chat.id,
        "Share your appeal reason:",
        reply_markup=kb
    )
    bot.register_next_step_handler(msg, save_appeal, group)

@bot.callback_query_handler(func=lambda c: c.data == "cancel_appeal")
def cancel_appeal(call):
    bot.send_message(call.message.chat.id, "❌ Appeal canceled.")

def save_appeal(message, group):
    if message.text.startswith("/cancel"):
        bot.send_message(message.chat.id, "❌ Appeal canceled.")
        return

    cur.execute(
        "INSERT INTO appeals VALUES (?,?,?,?)",
        (message.from_user.id, group, message.text, str(datetime.now()))
    )
    db.commit()

    bot.send_message(message.chat.id, "✅ Appeal submitted.")

    bot.send_message(
        OWNER_ID,
        f"📢 <b>NEW APPEAL</b>\n"
        f"👤 {message.from_user.first_name}\n"
        f"🆔 {message.from_user.id}\n"
        f"📍 Group: {group}\n"
        f"📝 {message.text}"
    )

# ---------- REPORT SYSTEM ----------

@bot.message_handler(commands=["report"])
def report(message):
    if not message.reply_to_message:
        bot.reply_to(message, "Reply to a message to report it.")
        return

    bot.send_message(message.chat.id, "✅ Report sent.")

    bot.forward_message(
        OWNER_ID,
        message.chat.id,
        message.reply_to_message.message_id
    )

    bot.send_message(
        OWNER_ID,
        f"🚨 <b>REPORT</b>\n"
        f"Reporter: @{message.from_user.username}\n"
        f"ID: {message.from_user.id}\n"
        f"Group: {message.chat.title}"
    )

# ---------- ANTI LINK / WARN SYSTEM ----------

@bot.message_handler(func=lambda m: m.chat.type in ["group", "supergroup"] and has_link(m.text))
def warn_link(message):
    if is_admin(message.chat.id, message.from_user.id):
        return

    cur.execute(
        "SELECT count FROM warnings WHERE user_id=? AND chat_id=?",
        (message.from_user.id, message.chat.id)
    )
    row = cur.fetchone()
    count = row[0] + 1 if row else 1

    cur.execute(
        "REPLACE INTO warnings VALUES (?,?,?)",
        (message.from_user.id, message.chat.id, count)
    )
    db.commit()

    if count >= MAX_WARNINGS:
        try:
            bot.restrict_chat_member(
                message.chat.id,
                message.from_user.id,
                until_date=datetime.now() + timedelta(seconds=AUTO_MUTE_SECONDS),
                can_send_messages=False
            )
            bot.reply_to(message, "🔇 You have been muted for 24 hours (4 warnings).")
        except:
            pass
    else:
        bot.reply_to(message, f"⚠️ Warning {count}/{MAX_WARNINGS}: Links are not allowed.")

print("Bot is running...")
bot.infinity_polling()
