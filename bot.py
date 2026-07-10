import random
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

players = []

async def mafia_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    players.clear()
    await update.message.reply_text("بدأت لعبة المافيا! أرسل /join للانضمام.")

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in [p['id'] for p in players]:
        players.append({'id': user.id, 'name': user.first_name})
        await update.message.reply_text(f"{user.first_name} انضم! العدد: {len(players)}")

async def start_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    num = len(players)
    if num < 6:
        await update.message.reply_text("العدد قليل، نحتاج 6 على الأقل.")
        return
    
    # توزيع الأدوار
    roles = ['مافيا', 'دكتور', 'شايب'] + ['مواطن'] * (num - 3) if num <= 8 else ['مافيا', 'مافيا', 'دكتور', 'شايب'] + ['مواطن'] * (num - 4)
    random.shuffle(roles)
    
    for i in range(num):
        try:
            await context.bot.send_message(chat_id=players[i]['id'], text=f"دورك: {roles[i]}")
        except:
            await update.message.reply_text(f"تعذر مراسلة {players[i]['name']} (لا تنسَ الضغط على Start في الخاص).")
    await update.message.reply_text("تم توزيع الأدوار في الخاص!")

if name == 'main':
    TOKEN = '7736606565:AAH_6w8UqOe6UCQ9Q4rsrv-aR_AfGcW-BZM'
    app = ApplicationBuilder().token(TOKEN).build()

    # هنا نقوم بتعريف القائمة التي ستظهر في البوت
    commands = [
        BotCommand("m", "بدء لعبة مافيا جديدة"),
        BotCommand("join", "الانضمام للعبة"),
        BotCommand("go", "بدء توزيع الأدوار")
    ]
    # هذا السطر هو الذي يظهر القائمة في الجروب
    app.bot.set_my_commands(commands)

    app.add_handler(CommandHandler("m", mafia_command))
    app.add_handler(CommandHandler("join", join_command))
    app.add_handler(CommandHandler("go", start_game_command))

    app.run_polling()
