import telebot
import time
import sqlite3
from datetime import datetime, timedelta
import threading

API_TOKEN = "8466680539:AAH4xYzLuoD2lg8nrL3J-81LJdeUraCu95o"
CHANNEL_ID = -1003863412599
ADMIN_ID = 8250437589
ADMIN_USERNAME = "@BestSellrs02"

bot = telebot.TeleBot(API_TOKEN)

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    expiry TEXT,
    active INTEGER,
    reminder_sent INTEGER DEFAULT 0
)
""")
conn.commit()


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id

    cursor.execute("INSERT OR IGNORE INTO users (user_id, active) VALUES (?, 0)", (user_id,))
    conn.commit()

    bot.send_message(user_id, f"""
👋 Welcome!

💰 Plan lene ke liye /buy likho

❓ Problem?
👉 https://t.me/{ADMIN_USERNAME}
""")


# ================= BUY =================
@bot.message_handler(commands=['buy'])
def buy(message):
    user_id = message.chat.id

    cursor.execute("SELECT active FROM users WHERE user_id=?", (user_id,))
    active = cursor.fetchone()[0]

    if active == 1:
        bot.send_message(user_id, "⚠️ Tumhara plan already active hai")
        return

    bot.send_message(user_id,
                     "💳 Payment karo\n\nPayment ke baad apna UTR number bhejo")


# ================= PAYMENT VERIFY =================
@bot.message_handler(func=lambda m: m.text.isdigit())
def utr(message):
    user_id = message.chat.id
    utr = message.text

    bot.send_message(user_id, "⏳ Payment verify ho raha hai...")

    # Admin ko bhejo
    bot.send_message(ADMIN_ID,
                     f"💰 New Payment Request\nUser: {user_id}\nUTR: {utr}\n\n/approve_{user_id}")


# ================= ADMIN APPROVE =================
@bot.message_handler(func=lambda m: m.text.startswith("/approve_"))
def approve(message):
    if message.chat.id != ADMIN_ID:
        return

    user_id = int(message.text.split("_")[1])

    expiry = datetime.now() + timedelta(minutes=10)

    cursor.execute("UPDATE users SET expiry=?, active=1, reminder_sent=0 WHERE user_id=?",
                   (expiry, user_id))
    conn.commit()

    invite = bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        member_limit=1
    )

    bot.send_message(user_id, f"""
✅ Payment verified!

🔗 Join:
{invite.invite_link}

⚠️ Sirf 1 user ke liye valid
""")


# ================= EXPIRY SYSTEM =================
def expiry_check():
    while True:
        now = datetime.now()

        cursor.execute("SELECT user_id, expiry, active, reminder_sent FROM users")
        data = cursor.fetchall()

        for user_id, expiry, active, reminder_sent in data:
            if active == 1 and expiry:
                expiry_time = datetime.fromisoformat(expiry)

                # expire
                if now >= expiry_time:
                    bot.send_message(user_id, "❌ Plan expired")
                    cursor.execute("UPDATE users SET active=0 WHERE user_id=?", (user_id,))
                    conn.commit()

                # reminder only once
                elif (expiry_time - now).total_seconds() <= 60 and reminder_sent == 0:
                    bot.send_message(user_id, "⚠️ Plan expiring in 1 minute")
                    cursor.execute("UPDATE users SET reminder_sent=1 WHERE user_id=?", (user_id,))
                    conn.commit()

        time.sleep(30)


# ================= ADMIN PANEL =================
@bot.message_handler(commands=['admin'])
def admin(message):
    if message.chat.id != ADMIN_ID:
        return

    bot.send_message(ADMIN_ID,
                     "👑 Admin Panel:\n/broadcast\n/users")


# ================= USERS =================
@bot.message_handler(commands=['users'])
def users_list(message):
    if message.chat.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    bot.send_message(ADMIN_ID, f"👥 Total Users: {count}")


# ================= BROADCAST =================
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.chat.id != ADMIN_ID:
        return

    bot.send_message(ADMIN_ID, "📢 Message bhejo")
    bot.register_next_step_handler(message, send_broadcast)


def send_broadcast(message):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for user in users:
        try:
            bot.send_message(user[0], message.text)
            time.sleep(0.5)
        except:
            pass

    bot.send_message(ADMIN_ID, "✅ Broadcast done")


# ================= CONTACT =================
@bot.message_handler(commands=['contact'])
def contact(message):
    bot.send_message(message.chat.id,
                     f"📩 Contact:\n👉 https://t.me/{ADMIN_USERNAME}")


# ================= RUN =================
threading.Thread(target=expiry_check).start()

print("Bot running...")
bot.infinity_polling()
