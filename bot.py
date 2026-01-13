import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time, re

TOKEN = "8389345826:AAH2yz5RrvOwvtQoW2ROG9E3-_ti7lKekMg"
OWNER_ID = 8286004637

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

appeals = {}
warns = {}

LINK_REGEX = r"(https?://|t\.me/|telegram\.me/)"

# ================= APPEAL SYSTEM =================

@bot.message_handler(commands=["start"])
def start(message):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("CHAT GC", callback_data="group_chat"),
        InlineKeyboardButton("Buy & Sell", callback_data="group_buy")
    )
    bot.send_message(
        message.chat.id,
        "Welcome! Choose a group to start your appeal.",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("group_"))
def choose_group(call):
    appeals[call.from_user.id] = {"group": call.data.replace("group_", "")}
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("Muted", callback_data="appeal_muted"),
        InlineKeyboardButton("Banned", callback_data="appeal_banned"),
        InlineKeyboardButton("Cancel", callback_data="appeal_cancel")
    )
    bot.edit_message_text(
        "You are not muted or banned.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("appeal_"))
def appeal_type(call):
    if call.data == "appeal_cancel":
        appeals.pop(call.from_user.id, None)
        bot.edit_message_text(
            "Appeal canceled.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    appeals[call.from_user.id]["type"] = call.data.replace("appeal_", "")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Cancel", callback_data="appeal_cancel"))
    bot.edit_message_text(
        "You are muted or banned.\nPlease reply with your appeal reason.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.from_user.id in appeals)
def appeal_reason(message):
    data = appeals.pop(message.from_user.id)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{message.from_user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{message.from_user.id}")
    )

    bot.send_message(
        OWNER_ID,
        f"📢 <b>NEW APPEAL</b>\n\n"
        f"👤 {message.from_user.first_name}\n"
        f"🆔 {message.from_user.id}\n"
        f"📍 Group: {data['group']}\n"
        f"⚠️ Type: {data['type']}\n"
        f"📝 Reason:\n{message.text}",
        reply_markup=kb
    )

    bot.reply_to(message, "✅ Appeal submitted.")

@bot.callback_query_handler(func=lambda c: c.data.startswith(("approve_", "reject_")))
def appeal_action(call):
    uid = int(call.data.split("_")[1])
    if call.data.startswith("approve"):
        bot.send_message(uid, "✅ Your appeal has been approved.")
    else:
        bot.send_message(uid, "❌ Your appeal has been rejected.")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# ================= REPORT SYSTEM (FIXED) =================

@bot.message_handler(commands=["report"])
def report(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a user's message to report.")
        return

    reported = message.reply_to_message

    # forward reported message
    bot.forward_message(
        OWNER_ID,
        reported.chat.id,
        reported.message_id
    )

    bot.send_message(
        OWNER_ID,
        f"🚨 <b>NEW REPORT</b>\n\n"
        f"👤 Name: {reported.from_user.first_name}\n"
        f"🆔 ID: {reported.from_user.id}\n"
        f"🔗 Username: @{reported.from_user.username or 'NoUsername'}\n"
        f"👥 Group: {reported.chat.title}"
    )

    bot.reply_to(message, "✅ Report sent.")

# ================= ANTI LINK / WARN =================

@bot.message_handler(func=lambda m: m.text and re.search(LINK_REGEX, m.text))
def warn_link(message):
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in ["administrator", "creator"]:
            return
    except:
        return

    uid = message.from_user.id
    warns[uid] = warns.get(uid, 0) + 1

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Remove Warn", callback_data=f"remwarn_{uid}"))

    if warns[uid] >= 4:
        bot.restrict_chat_member(
            message.chat.id,
            uid,
            until_date=int(time.time()) + 86400
        )
        bot.send_message(
            message.chat.id,
            f"🔇 {message.from_user.first_name} muted for 24 hours (4/4 warnings)"
        )
        warns[uid] = 0
    else:
        bot.reply_to(
            message,
            f"🚫 Links sending is not allowed\n⚠️ Warning {warns[uid]}/4",
            reply_markup=kb
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("remwarn_"))
def remove_warn(call):
    try:
        member = bot.get_chat_member(call.message.chat.id, call.from_user.id)
        if member.status not in ["administrator", "creator"]:
            return
    except:
        return

    uid = int(call.data.split("_")[1])
    warns[uid] = 0
    bot.edit_message_text(
        "✅ Warning removed by admin.",
        call.message.chat.id,
        call.message.message_id
    )

# ================= RUN =================

bot.infinity_polling()
