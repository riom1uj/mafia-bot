import random
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# هيكل بيانات اللعبة
game = {
    "is_running": False,
    "phase": None, 
    "players": [], # كل لاعب: {'id': id, 'name': name, 'role': None, 'is_alive': True}
    "night_actions": {"mafia": None, "doctor": None, "seer": None}
}

async def mafia_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game["players"] = []
    game["is_running"] = True
    await update.message.reply_text("بدأت لعبة المافيا! أرسل /join للانضمام.")

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game["is_running"]: return
    user = update.effective_user
    if user.id not in [p['id'] for p in game["players"]]:
        game["players"].append({'id': user.id, 'name': user.first_name, 'role': None, 'is_alive': True})
        await update.message.reply_text(f"تم انضمام {user.first_name}، العدد: {len(game['players'])}")

async def start_night(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    game["phase"] = "Night"
    await context.bot.send_message(chat_id=chat_id, text="🌙 حل الظلام.. تفقدوا رسائلكم الخاصة لاتخاذ قراراتكم!")

    # تجهيز الأزرار (قائمة اللاعبين)
    keyboard = [[InlineKeyboardButton(p['name'], callback_data=str(p['id']))] for p in game["players"] if p['is_alive']]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for p in game["players"]:
        if p['role'] == 'مافيا':
            await context.bot.send_message(p['id'], "أنت المافيا، اختر من تقتل:", reply_markup=reply_markup)
        elif p['role'] == 'دكتور':
            await context.bot.send_message(p['id'], "أنت الدكتور، اختر من تحمي:", reply_markup=reply_markup)
        elif p['role'] == 'شايب':
            await context.bot.send_message(p['id'], "أنت الشايب، اختر من تكشف:", reply_markup=reply_markup)

# التعامل مع ضغط الأزرار
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    player_id = int(query.data)
    user_id = query.from_user.id
    
    # تحديد الدور بناءً على من ضغط
    player = next((p for p in game["players"] if p['id'] == user_id), None)
    target = next((p for p in game["players"] if p['id'] == player_id), None)

    if player['role'] == 'مافيا': game["night_actions"]["mafia"] = target['id']
    elif player['role'] == 'دكتور': game["night_actions"]["doctor"] = target['id']
    elif player['role'] == 'شايب': 
        await query.edit_message_text(f"كشف: {target['name']} هو {target['role']}")
        return

    await query.edit_message_text(f"تم اختيار {target['name']} بنجاح.")

async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(game["players"]) < 6:
        await update.message.reply_text("نحتاج 6 لاعبين على الأقل.")
        return
    
    roles = ['مافيا', 'دكتور', 'شايب'] + ['مواطن'] * (len(game["players"]) - 3)
    random.shuffle(roles)
    for i, p in enumerate(game["players"]):
        p['role'] = roles[i]
        await context.bot.send_message(p['id'], f"دورك هو: {p['role']}")
    
    await update.message.reply_text("تم توزيع الأدوار. ستبدأ الليلة بعد 10 ثوانٍ.")
    context.job_queue.run_once(start_night, 10, chat_id=update.effective_chat.id)

if __name__ == '__main__':
    TOKEN = '7736606565:AAH_6w8UqOe6UCQ9Q4rsrv-aR_AfGcW-BZM'
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("m", mafia_command))
    app.add_handler(CommandHandler("join", join_command))
    app.add_handler(CommandHandler("go", go_command))
    app.add_handler(CallbackQueryHandler(button_click))
    
    app.run_polling()
