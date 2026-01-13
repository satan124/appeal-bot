import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import uuid

BOT_TOKEN = "8389345826:AAH2yz5RrvOwvtQoW2ROG9E3-_ti7lKekMg"
OWNER_ID = 8286004637

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

user_state = {}
appeal_data = {}
appeals = {}  # appeal_id -> data

GROUPS = ["CHAT GC", "BUY & SELL", "RECOVERY"]
APPEAL_TYPES = ["Muted", "Banned", "Warned", "Other"]

# ===== START =====
@bot.message_handler(commands=['start'])
def start(message):
    kb = InlineKeyboardMarkup()
    for g in GROUPS:
        kb.add(InlineKeyboardButton(g, callback_data=f"group:{g}"))
    bot.send_message(
        message.chat.id,
        "Welcome! Choose a group to start your appeal.",
        reply_markup=kb
    )

# ===== GROUP SELECT =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("group:"))
def select_group(call):
    group = call.data.split(":", 1)[1]
    appeal_data[call.message.chat.id] = {"group": group}
    user_state[call.message.chat.id] = "choose_type"

    kb = InlineKeyboardMarkup()
    for t in APPEAL_TYPES:
        kb.add(InlineKeyboardButton(t, callback_data=f"type:{t}"))
    kb.add(InlineKeyboardButton("❌ Cancel", callback_data="cancel"))

    bot.edit_message_text(
        f"Selected group: *{group}*\nChoose appeal type:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ===== TYPE SELECT =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("type:"))
def select_type(call):
    t = call.data.split(":", 1)[1]
    appeal_data[call.message.chat.id]["type"] = t
    user_state[call.message.chat.id] = "await_reason"

    bot.edit_message_text(
        f"Appeal type: *{t}*\n\nShare your appeal reason:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

# ===== CANCEL =====
@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(call):
    user_state.pop(call.message.chat.id, None)
    appeal_data.pop(call.message.chat.id, None)
    bot.edit_message_text(
        "❌ Appeal cancelled.",
        call.message.chat.id,
        call.message.message_id
    )

# ===== REASON INPUT =====
@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "await_reason")
def get_reason(message):
    appeal_data[message.chat.id]["reason"] = message.text
    user_state[message.chat.id] = "confirm"

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Submit Appeal", callback_data="submit"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
    )

    bot.send_message(
        message.chat.id,
        "Please confirm your appeal:",
        reply_markup=kb
    )

# ===== SUBMIT =====
@bot.callback_query_handler(func=lambda c: c.data == "submit")
def submit(call):
    data = appeal_data.get(call.message.chat.id)
    u = call.from_user

    appeal_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    appeals[appeal_id] = {
        "user_id": u.id,
        "group": data["group"],
        "type": data["type"],
        "reason": data["reason"]
    }

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{appeal_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject:{appeal_id}")
    )

    admin_msg = (
        f"📩 *NEW APPEAL*\n\n"
        f"🆔 Appeal ID: `{appeal_id}`\n"
        f"🏷 Group: {data['group']}\n"
        f"⚠️ Type: {data['type']}\n\n"
        f"👤 User: {u.first_name}\n"
        f"🆔 User ID: `{u.id}`\n\n"
        f"📝 Reason:\n{data['reason']}\n\n"
        f"🕒 {now}"
    )

    bot.send_message(OWNER_ID, admin_msg, reply_markup=kb, parse_mode="Markdown")

    bot.edit_message_text(
        "✅ Your appeal has been submitted.\nPlease wait for admin review.",
        call.message.chat.id,
        call.message.message_id
    )

    user_state.pop(call.message.chat.id, None)
    appeal_data.pop(call.message.chat.id, None)

# ===== APPROVE =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve:"))
def approve(call):
    appeal_id = call.data.split(":", 1)[1]
    data = appeals.get(appeal_id)

    if not data:
        bot.answer_callback_query(call.id, "Appeal not found.")
        return

    bot.send_message(
        data["user_id"],
        f"✅ *Your appeal has been APPROVED*\n\n"
        f"Group: {data['group']}\n"
        f"Type: {data['type']}",
        parse_mode="Markdown"
    )

    bot.edit_message_text(
        f"✅ Appeal `{appeal_id}` approved.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

    appeals.pop(appeal_id, None)

# ===== REJECT =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject:"))
def reject(call):
    appeal_id = call.data.split(":", 1)[1]
    data = appeals.get(appeal_id)

    if not data:
        bot.answer_callback_query(call.id, "Appeal not found.")
        return

    bot.send_message(
        data["user_id"],
        f"❌ *Your appeal has been REJECTED*\n\n"
        f"Group: {data['group']}\n"
        f"Type: {data['type']}",
        parse_mode="Markdown"
    )

    bot.edit_message_text(
        f"❌ Appeal `{appeal_id}` rejected.",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

    appeals.pop(appeal_id, None)

bot.infinity_polling()
