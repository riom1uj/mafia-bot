import random
import asyncio
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, PollAnswerHandler, ContextTypes

# هيكل بيانات اللعبة
game = {
    "is_running": False,
    "phase": None,  # None, Night, Day, Voting
    "chat_id": None,
    "players": [],  # قائمة اللاعبين الأحياء: {'id': id, 'name': name, 'role': None, 'is_alive': True}
    "night_actions": {"mafia": None, "doctor": None},
    "current_poll_id": None,
    "voting_results": {}  # لحساب الأصوات: {player_id: count}
}

# أمر بدء لعبة جديدة
async def mafia_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if game["is_running"]:
        await update.message.reply_text("⚠️ **هناك لعبة قيد التشغيل بالفعل!** يمكنك إنهاؤها باستخدام أمر /stop أولاً.")
        return
        
    game["players"] = []
    game["is_running"] = True
    game["chat_id"] = update.effective_chat.id
    game["phase"] = None
    game["night_actions"] = {"mafia": None, "doctor": None}
    
    await update.message.reply_text(
        "🎮 **═╝ تفضلووووا! بدأت لعبة المافيا ╚═**\n\n"
        "📢 أرسلوا أمر `/join` الآن للانضمام إلى المعركة!\n"
        "⚙️ للمشرفين: يمكنك إيقاف اللعبة في أي وقت عبر أمر `/stop`."
    )

# أمر الانضمام للعبة
async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game["is_running"]:
        await update.message.reply_text("❌ **لا توجد لعبة مفتوحة حالياً.** أرسل `/m` لإنشاء لعبة جديدة.")
        return
    if game["phase"] is not None:
        await update.message.reply_text("⚠️ **عذراً!** اللعبة بدأت بالفعل ولا يمكن الدخول في منتصف الجولة.")
        return
        
    user = update.effective_user
    if user.id not in [p['id'] for p in game["players"]]:
        game["players"].append({'id': user.id, 'name': user.first_name, 'role': None, 'is_alive': True})
        await update.message.reply_text(f"✨ انضمام مـمـيـز: ` {user.first_name} ` ✅\n👥 العدد الحالي: **{len(game['players'])}** لاعبين.")
    else:
        await update.message.reply_text("سجلت اسمك سابقاً يا بطل! انتظر بدء الجولة.")

# أمر إغلاق وإنهاء اللعبة فوراً (الأمر الجديد)
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game["is_running"]:
        await update.message.reply_text("ℹ️ **لا توجد لعبة تشغيل حالياً ليتم إيقافها.**")
        return

    # إلغاء أي مؤقتات زاوية في الخلفية (الليل والتصويت) لتفادي الأخطاء
    current_jobs = context.job_queue.jobs()
    for job in current_jobs:
        job.schedule_removal()

    # إعادة تصفير الهيكل بالكامل
    game["is_running"] = False
    game["phase"] = None
    game["players"] = []
    game["night_actions"] = {"mafia": None, "doctor": None}
    game["current_poll_id"] = None
    game["voting_results"] = {}

    await update.message.reply_text(
        "🛑 **🛑 تم إيقاف اللعبة وإغلاقها فوراً بنجاح!**\n"
        "🧹 تم إعادة تصفير كافة البيانات والجولات. يمكنك الآن بدء لعبة جديدة تماماً بأمر `/m`."
    )

# دالة التذكير قبل 30 ثانية من انتهاء الليل
async def night_reminder(context: ContextTypes.DEFAULT_TYPE):
    if game["phase"] == "Night":
        await context.bot.send_message(
            chat_id=game["chat_id"], 
            text="⏳ **[ تذكير دقيقة ونصف ]**\nبقي **30 ثانية فقط** وينتهي الليل! أسرعوا باتخاذ قراراتكم السرية بالخاص 🤫."
        )

# دالة الصباح وإعلان النتائج
async def start_morning(context: ContextTypes.DEFAULT_TYPE):
    if game["phase"] != "Night": return
    game["phase"] = "Day"
    chat_id = game["chat_id"]
    
    mafia_target_id = game["night_actions"]["mafia"]
    doctor_target_id = game["night_actions"]["doctor"]
    
    await context.bot.send_message(chat_id, "🌅 **═╝ أشرقت الشمس وحل الصباح ╚═**\nاستيقظت المدينة.. فلنرى أحداث الليلة المظلمة:")
    await asyncio.sleep(2)

    if mafia_target_id:
        if mafia_target_id == doctor_target_id:
            target_player = next((p for p in game["players"] if p['id'] == mafia_target_id), None)
            await context.bot.send_message(chat_id, f"🛡️ **حماية خارقة!** حاول المافيا اغتيال ` {target_player['name']} `، ولكن **الدكتور 🧪** قام بحمايته بنجاح! لم يمت أحد.")
        else:
            dead_player = next((p for p in game["players"] if p['id'] == mafia_target_id), None)
            if dead_player:
                dead_player['is_alive'] = False
                await context.bot.send_message(chat_id, f"💀 **جريمة في الظلام!** للأسف استيقظت المدينة على خبر اغتيال المغدور: ` {dead_player['name']} ` 🩸.")
    else:
        await context.bot.send_message(chat_id, "🕊️ **ليلة هادئة:** مرت هذه الليلة بسلام وأمان تام، ولم يتعرض أحد لأي مكروه.")

    game["night_actions"] = {"mafia": None, "doctor": None}
    if await check_game_over(context): return

    await context.bot.send_message(
        chat_id, 
        "🗣️ **مرحلة النقاش مفتوحة الآن!**\nتحدثوا بحرية، وعندما تجهزون لردع المتهمين، أرسلوا أمر `/vote` لإطلاق استطلاع التصويت."
    )

# دالة بدء الليل وإرسال الأزرار
async def start_night(context: ContextTypes.DEFAULT_TYPE):
    game["phase"] = "Night"
    chat_id = game["chat_id"]
    await context.bot.send_message(chat_id, "🌑 **🌌 خيّم الظلام ونامت المدينة...**\nأصحاب الأدوار، توجهوا إلى رسائلكم الخاصة لاتخاذ القرار!")

    keyboard = [[InlineKeyboardButton(p['name'], callback_data=str(p['id']))] for p in game["players"] if p['is_alive']]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for p in game["players"]:
        if not p['is_alive']: continue
        try:
            if p['role'] == 'مافيا':
                mafia_keyboard = [[InlineKeyboardButton(pl['name'], callback_data=str(pl['id']))] for pl in game["players"] if pl['is_alive'] and pl['role'] != 'مافيا']
                await context.bot.send_message(p['id'], "🔴 **🩸 أنت المافيا (القاتل)!**\nاختر ضحيتك الليلة من القائمة لإنهاء أمره:", reply_markup=InlineKeyboardMarkup(mafia_keyboard))
            elif p['role'] == 'دكتور':
                await context.bot.send_message(p['id'], "🟢 **🧪 أنت الدكتور (صمام الأمان)!**\nاختر من تريد حمايته من غدر المافيا الليلة:", reply_markup=reply_markup)
            elif p['role'] == 'شايب':
                await context.bot.send_message(p['id'], "🔍 **👁️ أنت الشايب (المحقق)!**\nاختر لاعباً لكشف قناعه ورؤية دوره الحقيقي سرياً:", reply_markup=reply_markup)
        except:
            await context.bot.send_message(chat_id, f"⚠️ **تنبيه:** تعذر مراسلة ` {p['name']} ` في الخاص، يرجى تفعيل البوت بالضغط على Start.")

    context.job_queue.run_once(night_reminder, 60)
    context.job_queue.run_once(start_morning, 90)

# استقبال ضغطات الأزرار
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    target_id = int(query.data)
    user_id = query.from_user.id
    
    player = next((p for p in game["players"] if p['id'] == user_id), None)
    target = next((p for p in game["players"] if p['id'] == target_id), None)

    if not player or game["phase"] != "Night": return

    if player['role'] == 'مافيا':
        game["night_actions"]["mafia"] = target['id']
        await query.edit_message_text(f"🎯 **تم تحديد الهدف:** اخترت اغتيال ` {target['name']} `.")
    elif player['role'] == 'دكتور':
        game["night_actions"]["doctor"] = target['id']
        await query.edit_message_text(f"🛡️ **تم التثبيت:** اخترت تقديم الرعاية والحماية لـ ` {target['name']} `.")
    elif player['role'] == 'شايب':
        await query.edit_message_text(f"👁️ **تقرير المحقق:** اللاعب ` {target['name']} ` دوره الحقيقي والسرّي هو: 【 **{target['role']}** 】.")

# توزيع الأدوار
async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game["is_running"] or game["phase"] is not None: return
    num = len(game["players"])
    if num < 6:
        await update.message.reply_text("❌ **العدد غير كافٍ!** نحتاج على الأقل إلى **6 لاعبين** لبدء اللعبة.")
        return
    
    if 6 <= num <= 8:
        roles = ['مافيا', 'دكتور', 'شايب'] + ['مواطن'] * (num - 3)
    elif 9 <= num <= 12:
        roles = ['مافيا', 'مافيا', 'دكتور', 'شايب'] + ['مواطن'] * (num - 4)
    else:
        await update.message.reply_text("❌ **العدد تخطى الحد!** الحد الأقصى المسموح به هو 12 لاعباً.")
        return

    random.shuffle(roles)
    
    names_list = "\n".join([f"👤 ` {p['name']} `" for p in game["players"]])
    await update.message.reply_text(f"🎲 **جاري خلط وتوزيع الأدوار سرياً...**\n\n📋 **قائمة المشتركين في هذه الجولة:**\n{names_list}")
    
    for i, p in enumerate(game["players"]):
        p['role'] = roles[i]
        try:
            await context.bot.send_message(p['id'], f"🎭 أهلاً بك ` {p['name']} `، دورك السري في هذه اللعبة هو: 【 **{p['role']}** 】")
        except:
            await update.message.reply_text(f"⚠️ **تنبيه مهم:** اللاعب ` {p['name']} ` لم يفعّل البوت في الخاص بعد!")
    
    await update.message.reply_text("📬 **تم إرسال الأدوار للجميع بالخاص!**\nستبدأ الليلة الأولى خلال 10 ثوانٍ، استعدوا...")
    context.job_queue.run_once(start_night, 10)

# فتح التصويت
async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if game["phase"] != "Day":
        await update.message.reply_text("⚠️ **عفواً!** التصويت متاح فقط في مرحلة النهار (الصباح).")
        return
    
    game["phase"] = "Voting"
    chat_id = game["chat_id"]
    
    options = [p['name'] for p in game["players"] if p['is_alive']]
    options.append("⏩ تخطي التصويت")
    
    poll_msg = await context.bot.send_poll(
        chat_id=chat_id,
        question="🗳️ ══╝ حان وقت القضاء على المجرمين ╚══\nمن هو الشخص المشتبه به في رأيكم؟ صوّتوا الآن:",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False
    )
    
    game["current_poll_id"] = poll_msg.poll.id
    game["voting_results"] = {p['id']: 0 for p in game["players"] if p['is_alive']}
    game["voting_results"]["skip"] = 0

    context.job_queue.run_once(end_voting, 60)

# استقبال أصوات الـ Poll
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    if answer.poll_id != game["current_poll_id"]: return
    
    alive_players = [p for p in game["players"] if p['is_alive']]
    chosen_index = answer.option_ids[0]
    
    if chosen_index < len(alive_players):
        voted_player_id = alive_players[chosen_index]['id']
        game["voting_results"][voted_player_id] = game["voting_results"].get(voted_player_id, 0) + 1
    else:
        game["voting_results"]["skip"] = game["voting_results"].get("skip", 0) + 1

# إنهاء التصويت
async def end_voting(context: ContextTypes.DEFAULT_TYPE):
    if game["phase"] != "Voting": return
    chat_id = game["chat_id"]
    
    await context.bot.send_message(chat_id, "🔒 **انتهى وقت التصويت!** جاري سحب الأوراق وفرز الأصوات بدقة...")
    await asyncio.sleep(2)

    results = game["voting_results"]
    max_votes = max(results.values()) if results else 0
    highest_voted_ids = [k for k, v in results.items() if v == max_votes]
    
    if max_votes == 0 or len(highest_voted_ids) > 1 or highest_voted_ids[0] == "skip":
        await context.bot.send_message(chat_id, "⏩ **تخطي:** تعادل الأصوات أو اختيار التخطي أنقذ الجميع! لم يطرد أحد في هذه الجولة.")
    else:
        kicked_id = highest_voted_ids[0]
        kicked_player = next((p for p in game["players"] if p['id'] == kicked_id), None)
        
        if kicked_player:
            kicked_player['is_alive'] = False
            
            if kicked_player['role'] == 'مافيا':
                await context.bot.send_message(chat_id, f"💥 **ضربة معلم!** تم نفي اللاعب ` {kicked_player['name']} ` بقرار الشعب، وتبين أنه: 🔥 【 **مافيا** 】!")
            else:
                await context.bot.send_message(chat_id, f"⚖️ **عدالة قاسية:** غادرنا اللاعب ` {kicked_player['name']} ` بقرار الأغلبية، دون كشف دوره (ليس مافيا).")

            try:
                mute_permissions = ChatPermissions(can_send_messages=False, can_send_polls=False, can_send_other_messages=False)
                await context.bot.restrict_chat_member(chat_id=chat_id, user_id=kicked_id, permissions=mute_permissions)
                await context.bot.send_message(chat_id, f"🤫 **تم كتم** الـمـطرود ` {kicked_player['name']} ` ليرقد في سلام تام خارج المحادثة.")
            except:
                await context.bot.send_message(chat_id, f"⚠️ **تنبيه:** لم أتمكن من كتم عضوية ` {kicked_player['name']} ` برمجياً (ربما لأنه مشرف بالجروب).")

    if await check_game_over(context): return
    
    await context.bot.send_message(chat_id, "💤 **تستعد القرية للنوم والظلام مجدداً...**\nتبدأ الليلة التالية خلال 10 ثوانٍ.")
    context.job_queue.run_once(start_night, 10)

# فحص الفوز
async def check_game_over(context: ContextTypes.DEFAULT_TYPE):
    alive_mafia = len([p for p in game["players"] if p['is_alive'] and p['role'] == 'مافيا'])
    alive_citizens = len([p for p in game["players"] if p['is_alive'] and p['role'] != 'مافيا'])
    chat_id = game["chat_id"]

    if alive_mafia == 0:
        await context.bot.send_message(chat_id, "🎉 **╝ انـتـصـرت الـقـريـة! ╚** 🎉\nتم إبادة المافيا وتطهير المدينة بالكامل! العباقرة يفوزون! 🥳")
        game["is_running"] = False
        return True
    elif alive_mafia >= alive_citizens:
        await context.bot.send_message(chat_id, "😈 **╝ انـتـصـرت الـمـافـيـا! ╚** 😈\nأحكمت المافيا قبضتها الدموية على المدينة وقضت على الجميع! الخطة نجحت 🩸.")
        game["is_running"] = False
        return True
    return False

if __name__ == '__main__':
    TOKEN = 'YOUR_BOT_TOKEN_HERE' 
    app = ApplicationBuilder().token(TOKEN).build()
    
    commands = [
        BotCommand("m", "بدء لعبة مافيا جديدة"),
        BotCommand("join", "انضمام للعبة الحالية"),
        BotCommand("go", "توزيع الأدوار وبدء اللعبة"),
        BotCommand("vote", "فتح استطلاع التصويت بالجروب"),
        BotCommand("stop", "إنهاء وإغلاق اللعبة الحالية فوراً")
    ]
    app.bot.set_my_commands(commands)
    
    app.add_handler(CommandHandler("m", mafia_command))
    app.add_handler(CommandHandler("join", join_command))
    app.add_handler(CommandHandler("go", go_command))
    app.add_handler(CommandHandler("vote", vote_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(PollAnswerHandler(handle_poll_answer))
    
    app.run_polling()
