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
last_sent = {}

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

    bot.send_photo(
        call.message.chat.id,
        open("qr.png", "rb"),
        caption=f"💰 Plan: {duration}\nPrice: {price}\n\nUPI: vinay-24@axl\n\nQR scan karke payment karo aur screenshot bhejo"
    )

    bot.answer_callback_query(call.id)

# SCREENSHOT
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    if m.chat.id in last_sent and time.time() - last_sent[m.chat.id] < 30:
        bot.reply_to(m, "⏳ Wait 30 sec before sending again")
        return

    last_sent[m.chat.id] = time.time()

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
        expire_date=int(time.time()) + 60
    )

    bot.send_message(
        user_id,
        f"✅ Approved\n⚠️ Link sirf 1 minute valid hai\n{link.invite_link}"
    )

    bot.answer_callback_query(c.id, "Approved")

# REJECT
@bot.callback_query_handler(func=lambda c: c.data.startswith("reject"))
def reject(c):
    user_id = int(c.data.split("_")[1])
    bot.send_message(user_id, "❌ Payment rejected")
    bot.answer_callback_query(c.id, "Rejected")

# BROADCAST
@bot.message_handler(commands=['broadcast'])
def broadcast(m):
    if m.chat.id != ADMIN_ID:
        return

    msg = m.text.replace("/broadcast ", "")
    count = 0

    for u in users:
        try:
            bot.send_message(u, msg)
            count += 1
        except:
            pass

    bot.send_message(ADMIN_ID, f"Sent to {count} users")

# USERS COUNT
@bot.message_handler(commands=['users'])
def users_count(m):
    if m.chat.id != ADMIN_ID:
        return
    bot.send_message(m.chat.id, f"Total active users: {len(users)}")

# AUTO REMOVE
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

# AUTO REMINDER
def reminder_check():
    sent_1day = set()
    sent_1hour = set()

    while True:
        now = datetime.now()

        for u in users:
            remaining = users[u] - now

            if 0 < remaining.total_seconds() <= 86400 and u not in sent_1day:
                try:
                    bot.send_message(u, "⏰ Subscription 1 day me expire hogi")
                    sent_1day.add(u)
                except:
                    pass

            if 0 < remaining.total_seconds() <= 3600 and u not in sent_1hour:
                try:
                    bot.send_message(u, "⚠️ Subscription 1 hour me expire hogi")
                    sent_1hour.add(u)
                except:
                    pass

        time.sleep(60)

# THREADS
threading.Thread(target=expiry_check).start()
threading.Thread(target=reminder_check).start()

bot.infinity_polling()
