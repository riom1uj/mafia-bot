from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import random
import asyncio

TOKEN = "7736606565:AAH_6w8UqOe6UCQ9Q4rsrv-aR_AfGcW-BZM"

players = []
roles = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(f"اهلا {name} 👋\nبوت المافيا اشتغل بنجاح!")

async def join(update: Update, context):
    user = update.effective_user
    if user not in players:
        players.append(user)
        await update.message.reply_text(f"✅ انضم {user.first_name} إلى اللعبة")
    else:
        await update.message.reply_text("انت داخل اللعبة بالفعل")

async def show_players(update, context):
    if players:
        text = "👥 اللاعبين في اللعبة:\n"
        for p in players:
            text += f"- {p.first_name}\n"
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("لا يوجد لاعبين بعد")

async def start_game(update, context):
    if len(players) < 3:
        await update.message.reply_text("❗️ على الأقل 3 لاعبين لبدء اللعبة")
        return

    mafia = random.choice(players)
    doctor = random.choice([p for p in players if p != mafia])
    detective = random.choice([p for p in players if p != mafia and p != doctor])

    await update.message.reply_text("🕵️ بدأت لعبة المافيا")

    for p in players:
        if p == mafia:
            roles[p.id] = "mafia"
            await context.bot.send_message(chat_id=p.id, text="🕵️ دورك: مافيا")
        elif p == doctor:
            roles[p.id] = "doctor"
            await context.bot.send_message(chat_id=p.id, text="💉 دورك: دكتور")
        elif p == detective:
            roles[p.id] = "detective"
            await context.bot.send_message(chat_id=p.id, text="🔍 دورك: الشايب")
        else:
            roles[p.id] = "citizen"
            await context.bot.send_message(chat_id=p.id, text="🙂 دورك: مواطن")

# إعداد البوت
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("join", join))
app.add_handler(CommandHandler("players", show_players))
app.add_handler(CommandHandler("startgame", start_game))

print("Bot is running...")
app.run_polling()
