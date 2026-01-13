import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import re

TOKEN = "8389345826:AAH2yz5RrvOwvtQoW2ROG9E3-_ti7lKekMg"
OWNER_ID = 8286004637

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

appeals = {}
reports = {}
warns = {}

LINK_REGEX = r"(https?://|t\.me/|telegram\.me/)"

# ---------------- START ----------------

@bot.message_handler(commands=["start"])
def start(message):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("CHAT GC", callback_data="group_chat"),
        InlineKeyboardButton("BUY & SELL", callback_data="group_bs")
    )
    bot.send_message(
        message.chat.id,
        "Welcome! Choose a group to start your appeal.",
        reply_markup=kb
    )

# ---------------- GROUP SELECT ----------------

@bot.callback_query_handler(func=lambda c: c.data.startswith("group_"))
def group_select(call):
    appeals[call.from_user.id] = {"group": call.data.replace("group_", "")}
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("Muted", callback_data="status_muted"),
        InlineKeyboardButton("Banned", callback_data="status_banned")
    )
    bot.edit_message_text(
        "You are muted or banned?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ---------------- STATUS ----------------

@bot.callback_query_handler(func=lambda c: c.data.startswith("status_"))
def status_select(call):
    appeals[call.from_user.id]["status"] = call.data.replace("status_", "")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Cancel", callback_data="cancel"))
    bot.edit_message_text(
        "Share your appeal reason:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ---------------- CANCEL ----------------

@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(call):
    appeals.pop(call.from_user.id, None)
    bot.edit_message_text(
        "Appeal canceled.",
        call.message.chat.id,
        call.message.message_id
    )

# ---------------- APPEAL TEXT ----------------

@bot.message_handler(func=lambda m: m.from_user.id in appeals)
def appeal_text(message):
    data = appeals.pop(message.from_user.id)
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"accept_{message.from_user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{message.from_user.id}")
    )

    bot.send_message(
        OWNER_ID,
        f"📢 <b>NEW APPEAL</b>\n"
        f"👤 {message.from_user.first_name}\n"
        f"🆔 {message.from_user.id}\n"
        f"📍 Group: {data['group']}\n"
        f"⚠️ Status: {data['status']}\n"
        f"📝 {message.text}",
        reply_markup=kb
    )

    bot.send_message(message.chat.id, "✅ Appeal submitted.")

# ---------------- APPROVE ----------------

@bot.callback_query_handler(func=lambda c: c.data.startswith("accept_"))
def approve(call):
    if call.from_user.id != OWNER_ID:
        return
    uid = int(call.data.split("_")[1])
    bot.send_message(uid, "✅ <b>Your appeal has been approved.</b>")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# ---------------- REJECT ----------------

@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(call):
    if call.from_user.id != OWNER_ID:
        return
    uid = int(call.data.split("_")[1])
    bot.send_message(uid, "❌ <b>Your appeal has been rejected.</b>")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# ---------------- REPORT ----------------

@bot.message_handler(commands=["report"])
def report(message):
    if not message.reply_to_message:
        bot.reply_to(message, "Reply to the message you want to report.")
        return

    reports[message.from_user.id] = message.reply_to_message
    bot.reply_to(
        message,
        "Create a proof group, add all screenshots,\nthen send me the group link."
    )

# ---------------- PROOF LINK ----------------

@bot.message_handler(func=lambda m: m.from_user.id in reports and re.search(LINK_REGEX, m.text))
def proof(message):
    reported = reports.pop(message.from_user.id)
    bot.forward_message(OWNER_ID, reported.chat.id, reported.message_id)

    bot.send_message(
        OWNER_ID,
        f"🚨 <b>REPORT</b>\n"
        f"Reporter: @{message.from_user.username or 'NoUsername'}\n"
        f"Reporter ID: {message.from_user.id}\n"
        f"Group: {reported.chat.title}\n"
        f"Proof Group: {message.text}"
    )

    bot.send_message(message.chat.id, "✅ Report submitted.")

# ---------------- ANTI LINK + WARN ----------------

@bot.message_handler(func=lambda m: re.search(LINK_REGEX, m.text or ""))
def anti_link(message):
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in ["administrator", "creator"]:
            return
    except:
        return

    uid = message.from_user.id
    warns[uid] = warns.get(uid, 0) + 1

    if warns[uid] >= 4:
        bot.restrict_chat_member(
            message.chat.id,
            uid,
            until_date=int(time.time()) + 86400
        )
        bot.send_message(message.chat.id, f"🔇 {message.from_user.first_name} muted (4 warns).")
        warns[uid] = 0
    else:
        bot.reply_to(message, f"⚠️ Warning {warns[uid]}/4")

# ---------------- RUN ----------------

bot.infinity_polling()
