import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import threading
import time

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = telebot.TeleBot(TOKEN)

users = {}
user_plans = {}

# SAVE / LOAD
def save():
    with open("users.txt", "w") as f:
        for u in users:
            f.write(f"{u},{users[u].isoformat()}\n")

def load():
    try:
        with open("users.txt") as f:
            for line in f:
                u, d = line.strip().split(",")
                users[int(u)] = datetime.fromisoformat(d)
    except:
        pass

load()

# START
@bot.message_handler(commands=['start'])
def start(m):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("💳 ₹50 - 1 Month", callback_data="plan_1"),
        InlineKeyboardButton("💳 ₹100 - 3 Months", callback_data="plan_3")
    )
    bot.send_message(m.chat.id, "Welcome 👋\nSelect Plan 👇", reply_markup=markup)

# PLAN SELECT
@bot.callback_query_handler(func=lambda call: call.data.startswith("plan"))
def select_plan(call):
    plan = call.data.split("_")[1]

    if plan == "1":
        price = "₹50"
        duration = "1 Month"
    else:
        price = "₹100"
        duration = "3 Months"

    user_plans[call.message.chat.id] = plan

    # QR + UPI send
    bot.send_photo(
        call.message.chat.id,
        open("qr.png", "rb"),
        caption=f"💰 Plan: {duration}\nPrice: {price}\n\nUPI: yourupi@upi\n\nQR scan karke payment karo aur screenshot bhejo"
    )

# SCREENSHOT HANDLE
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    bot.forward_message(ADMIN_ID, m.chat.id, m.message_id)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{m.chat.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{m.chat.id}")
    )

    bot.send_message(ADMIN_ID, f"User ID: {m.chat.id}", reply_markup=markup)
    bot.reply_to(m, "Screenshot admin ko bhej diya gaya ✅")

# APPROVE
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve"))
def approve(c):
    user_id = int(c.data.split("_")[1])

    plan = user_plans.get(user_id, "1")

    if plan == "1":
        expiry = datetime.now() + timedelta(days=30)
    else:
        expiry = datetime.now() + timedelta(days=90)

    users[user_id] = expiry
    save()

    link = bot.create_chat_invite_link(
        CHANNEL_ID,
        member_limit=1,
        expire_date=int(time.time()) + 300
    )

    bot.send_message(user_id, f"✅ Approved\nJoin: {link.invite_link}")
    bot.answer_callback_query(c.id, "Approved")

# REJECT
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject"))
def reject(c):
    user_id = int(c.data.split("_")[1])
    bot.send_message(user_id, "❌ Payment rejected")
    bot.answer_callback_query(c.id, "Rejected")

# AUTO EXPIRY
def expiry_check():
    while True:
        now = datetime.now()
        for u in list(users):
            if users[u] < now:
                try:
                    bot.ban_chat_member(CHANNEL_ID, u)
                    bot.unban_chat_member(CHANNEL_ID, u)
                    del users[u]
                    save()
                except:
                    pass
        time.sleep(60)

threading.Thread(target=expiry_check).start()

bot.infinity_polling()
