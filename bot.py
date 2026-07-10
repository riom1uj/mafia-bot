    import random
import asyncio
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, PollAnswerHandler, ContextTypes

# هيكل بيانات اللعبة
game = {
    "is_running": False,
    "phase": None,  # None, Night, Day, Voting
    "chat_id": None,
    "players": [],  # قائمة اللاعبين: {'id': id, 'name': name, 'role': None, 'is_alive': True}
    "night_actions": {"mafia": None, "doctor": None},
    "current_poll_id": None,
    "voting_results": {}
}

async def mafia_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game["players"] = []
    game["is_running"] = True
    game["chat_id"] = update.effective_chat.id
    game["phase"] = None
    await update.message.reply_text(
        "🎮 *ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ*\n"
        "🔥 *بـدأت لـعـبـة الـمـافـيـا الـكـبـرى‌‏!* 🔥\n"
        "أرسل الأمر /join الآن للدخول في المعركة⚔️\n"
        "*ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ*", 
        parse_mode='Markdown'
    )

async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game["is_running"] or game["phase"] is not None:
        await update.message.reply_text("⚠️ *عذراً، لا يمكنك الانضمام الآن اللعبة بدأت بالفعل!*", parse_mode='Markdown')
        return
    user = update.effective_user
    if user.id not in [p['id'] for p in game["players"]]:
        game["players"].append({'id': user.id, 'name': user.first_name, 'role': None, 'is_alive': True})
        await update.message.reply_text(
            f"📥 ✅ *تم انضمام اللاعب:* {user.first_name}\n"
            f"📊 *العدد الحالي للتحالف:* [ {len(game['players'])} ]", 
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("⚠️ *أنت مسجل ومستعد للمعركة بالفعل!*", parse_mode='Markdown')

async def night_reminder(context: ContextTypes.DEFAULT_TYPE):
    if game["phase"] == "Night":
        await context.bot.send_message(
            chat_id=game["chat_id"], 
            text="⏳ 🔴 *تنبيه أخير:* متبقي 30 ثانية فقط وينتهي الليل! أسرعوا باتخاذ قراراتكم السريّة.",
            parse_mode='Markdown'
        )

async def start_morning(context: ContextTypes.DEFAULT_TYPE):
    if game["phase"] != "Night": return
    game["phase"] = "Day"
    chat_id = game["chat_id"]
    
    mafia_target_id = game["night_actions"]["mafia"]
    doctor_target_id = game["night_actions"]["doctor"]
    
    await context.bot.send_message(
        chat_id, 
        "🌅 🌤️ *أشـرقـت الـشـمـس وحـلّ الـصـبـاح...*\n"
        "يتثاءب أهل القرية هاربين من كابوس الليل، فلنرى ما حدث!",
        parse_mode='Markdown'
    )
    await asyncio.sleep(2)

    if mafia_target_id:
        target_player = next((p for p in game["players"] if p['id'] == mafia_target_id), None)
        if mafia_target_id == doctor_target_id:
            await context.bot.send_message(
                chat_id, 
                f"🛡️ 🟢 *محاولة اغتيال فاشلة!*\n"
                f"تسلل المافيا لقتل اللاعب {target_player['name']}، "
                f"ولكن *الدكتور الشجاع* كان مختبئاً وحماه في الوقت المناسب! [ لا وفيات ] ✨",
                parse_mode='Markdown'
            )
        else:
            if target_player:
                target_player['is_alive'] = False
                await context.bot.send_message(
                    chat_id, 
                    f"💀 🩸 *جريمة بشعة هزّت أركان المدينة!*\n"
                    f"استيقظ الجميع على بركة من الدماء.. تم اغتيال اللاعب: \n"
                    f"👉 *【 {target_player['name']} 】* واختفى أثره تماماً 🪦",
                    parse_mode='Markdown'
                )
    else:
        await context.bot.send_message(
            chat_id, 
            "🕊️ ✨ *يا لروعة هذه الليلة!* مرت بسلام تام ولم تُسفك أي دماء في المدينة.",
            parse_mode='Markdown'
        )

    game["night_actions"] = {"mafia": None, "doctor": None}
    if await check_game_over(context): return

  await context.bot.send_message(
        chat_id, 
        "🗣️ 👥 *مرحلة النقاش والشكوك مفتوحة الآن!*\n"
        "تبادلوا الاتهامات وابحثوا عن المجرمين. عندما تستقرون، أرسلوا الأمر /vote لفتح صناديق الاقتراع وطرد المتهم.",
        parse_mode='Markdown'
    )

async def start_night(context: ContextTypes.DEFAULT_TYPE):
    game["phase"] = "Night"
    chat_id = game["chat_id"]
    await context.bot.send_message(
        chat_id, 
        "🌌 🌑 *حـلّ الـظـلام الـدامـس.. نـامـت الـمـديـنـة...*\n"
        "🤫 يرجى الهدوء تماماً، حان وقت استيقاظ القوى الخفية بالخاص وبدء المؤامرات.",
        parse_mode='Markdown'
    )

    keyboard = [[InlineKeyboardButton(p['name'], callback_data=str(p['id']))] for p in game["players"] if p['is_alive']]

    for p in game["players"]:
        if not p['is_alive']: continue
        try:
            if p['role'] == 'مافيا':
                mafia_keyboard = [[InlineKeyboardButton(pl['name'], callback_data=str(pl['id']))] for pl in game["players"] if pl['is_alive'] and pl['role'] != 'مافيا']
                await context.bot.send_message(p['id'], "🩸 🔴 *أنت المافيا (رأس الأفعى):*\nاختر الضحية البائسة التي تريد تصفيتها الليلة:", reply_markup=InlineKeyboardMarkup(mafia_keyboard), parse_mode='Markdown')
            elif p['role'] == 'دكتور':
                await context.bot.send_message(p['id'], "🧪 🟢 *أنت الدكتور (ملاك الرحمة):*\nاختر الشخص الذي تريد حمايته من رصاص المافيا الليلة:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            elif p['role'] == 'شايب':
                await context.bot.send_message(p['id'], "👁️ 🔵 *أنت الشايب (العين الحكيمة):*\nاختر شخصاً لتكشف أوراقه وتعرف دوره الحقيقي سرّاً:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except:
            await context.bot.send_message(chat_id, f"⚠️ *تنبيه:* تعذر إرسال الخيارات للاعب {p['name']} بالخاص (يجب أن يفعل البوت أولاً).", parse_mode='Markdown')

    context.job_queue.run_once(night_reminder, 60)
    context.job_queue.run_once(start_morning, 90)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    target_id = int(query.data)
    user_id = query.from_user.id
    
    player = next((p for p in game["players"] if p['id'] == user_id), None)
    target = next((p for p in game["players"] if p['id'] == target_id), None)

    if not player or game["phase"] != "Night": return

    if player['role'] == 'مافيا':
        game["night_actions"]["mafia"] = target['id']
        await query.edit_message_text(f"🎯 🔴 *صدر أمر الاغتيال المباشر ضد:* {target['name']}", parse_mode='Markdown')
    elif player['role'] == 'دكتور':
        game["night_actions"]["doctor"] = target['id']
        await query.edit_message_text(f"🛡️ 🟢 *وضعت درع الحماية والمراقبة على:* {target['name']}", parse_mode='Markdown')
    elif player['role'] == 'شايب':
        await query.edit_message_text(f"👁️ 🔍 *كشف البصيرة السري:* \nاللاعب {target['name']} دوره الحقيقي هو:  *【 {target['role']} 】*", parse_mode='Markdown')

async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game["is_running"] or game["phase"] is not None: return
    num = len(game["players"])
    if num < 6:
        await update.message.reply_text("❌ *لا يمكن البدء! نحتاج 6 مقاتلين على الأقل لخوض اللعبة.*", parse_mode='Markdown')
        return
    
    if 6 <= num <= 8:
        roles = ['مافيا', 'دكتور', 'شايب'] + ['مواطن'] * (num - 3)
    elif 9 <= num <= 12:
        roles = ['مافيا', 'مافيا', 'دكتور', 'شايب'] + ['مواطن'] * (num - 4)
    else:
        await update.message.reply_text("❌ *العدد مفرط جداً! (الحد الأقصى هو 12 لاعب فقط).*")
        return

    random.shuffle(roles)
    
    names_list = "\n".join([f"👤 ▪️ {p['name']}" for p in game["players"]])

await update.message.reply_text(
        f"🎲 *ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ*\n"
        f"🔮 *جـاري سـحـب وتـوزيـع الأدوار الـسـرّيـة...*\n\n"
        f"*قائمة ساحة اللعب الحالية:*\n{names_list}\n"
        f"*ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ*", 
        parse_mode='Markdown'
    )
    
    for i, p in enumerate(game["players"]):
        p['role'] = roles[i]
        try:
            await context.bot.send_message(p['id'], f"🎭 *بطاقتك السرية للعبة المافيا:* \nأنت تلعب الآن بدور:  *【 {p['role']} 】*", parse_mode='Markdown')
        except:
            await update.message.reply_text(f"⚠️ *عذراً!* اللاعب {p['name']} لم يضغط Start بالخاص مع البوت، لن تصله الأدوار!", parse_mode='Markdown')
    
    await update.message.reply_text("📬 *تطايرت الأوراق! وصلت الأدوار للجميع في الخاص سرّاً.*\n⏳ ستبدأ أولى الليالي المظلمة خلال 10 ثوانٍ... استعدوا!", parse_mode='Markdown')
    context.job_queue.run_once(start_night, 10)

async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if game["phase"] != "Day":
        await update.message.reply_text("⚠️ *التصويت متاح فقط في وضح النهار وأمام الجميع!*", parse_mode='Markdown')
        return
    
    game["phase"] = "Voting"
    chat_id = game["chat_id"]
    
    options = [p['name'] for p in game["players"] if p['is_alive']]
    options.append("⏩ تخطي التصويت الحالي")
    
    poll_msg = await context.bot.send_poll(
        chat_id=chat_id,
        question="🗳️ ⚖️ [ قضاء الشعب ] حان وقت المحاكمة! من تعتقدون أنه الخائن (المافيا)؟",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False
    )
    
    game["current_poll_id"] = poll_msg.poll.id
    game["voting_results"] = {p['id']: 0 for p in game["players"] if p['is_alive']}
    game["voting_results"]["skip"] = 0

    context.job_queue.run_once(end_voting, 60)

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

async def end_voting(context: ContextTypes.DEFAULT_TYPE):
    if game["phase"] != "Voting": return
    chat_id = game["chat_id"]
    
    await context.bot.send_message(chat_id, "🔒 *أُغلقت صناديق الاقتراع! جاري فرز وحساب الأصوات...*", parse_mode='Markdown')
    await asyncio.sleep(2)

    results = game["voting_results"]
    max_votes = max(results.values()) if results else 0
    highest_voted_ids = [k for k, v in results.items() if v == max_votes]
    
    if max_votes == 0 or len(highest_voted_ids) > 1 or highest_voted_ids[0] == "skip":
        await context.bot.send_message(chat_id, "⏩ *رُفعت الجلسة!* تعادلت الأصوات أو فضّل الجميع *التخطي*، لن يُطرد أحد في هذه الجولة.", parse_mode='Markdown')
    else:
        kicked_id = highest_voted_ids[0]
        kicked_player = next((p for p in game["players"] if p['id'] == kicked_id), None)
        
        if kicked_player:
            kicked_player['is_alive'] = False
            
            if kicked_player['role'] == 'مافيا':
                await context.bot.send_message(chat_id, f"💥 👺 *ضربة قاضية للعدو!*\nبأغلبية ساحقة تم نفي وطرد اللاعب *【 {kicked_player['name']} 】*، وتبين باليقين أنه كان من أفراد *[ المافيا ]*! 🔥", parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id, f"⚖️ 💔 *ظلم العدالة القاسي!*\nبقرار من الشعب تم نفي اللاعب *【 {kicked_player['name']} 】* خارج أسوار القرية، ولم يكن من المافيا! دمه في رقابكم المستعجلة 🥺", parse_mode='Markdown')

          try:
                mute_permissions = ChatPermissions(can_send_messages=False, can_send_polls=False, can_send_other_messages=False)
                await context.bot.restrict_chat_member(chat_id=chat_id, user_id=kicked_id, permissions=mute_permissions)
                await context.bot.send_message(chat_id, f"🤫 *أُطبق الصمت!* تم كتم صوت المطرود {kicked_player['name']}، الموتى والأسرى لا يتحدثون.", parse_mode='Markdown')
            except:
                pass

    if await check_game_over(context): return
    
    await context.bot.send_message(chat_id, "💤 *تستعد القرية للنوم مجدداً وعيونها تترقب..* تبدأ الليلة التالية بعد 10 ثوانٍ.", parse_mode='Markdown')
    context.job_queue.run_once(start_night, 10)

async def check_game_over(context: ContextTypes.DEFAULT_TYPE):
    alive_mafia = len([p for p in game["players"] if p['is_alive'] and p['role'] == 'مافيا'])
    alive_citizens = len([p for p in game["players"] if p['is_alive'] and p['role'] != 'مافيا'])
    chat_id = game["chat_id"]

    if alive_mafia == 0:
        await context.bot.send_message(
            chat_id, 
            "🎉 ✨ *ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ*\n"
            "🥳 *انـتـصـرت الـقـريـة الـمـسـالـمـة!* 🥳\n"
            "تم القضاء وبنجاح باهر على آخر جرذ من أفراد المافيا البائسة وعاد الأمان!\n"
            "*ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ*", 
            parse_mode='Markdown'
        )
        game["is_running"] = False
        return True
    elif alive_mafia >= alive_citizens:
        await context.bot.send_message(
            chat_id, 
            "🩸 😈 *ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ*\n"
            "💀 *انـتـصـرت الـمـافـيـا الـدمـويـة!* 💀\n"
            "سقطت المدينة بالكامل تحت وطأة الظلام وتصفية آخر مواطن شريف.. العب غيرها!\n"
            "*ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ*", 
            parse_mode='Markdown'
        )
        game["is_running"] = False
        return True
    return False

if name == 'main':
    TOKEN = '7736606565:AAH_6w8UqOe6UCQ9Q4rsrv-aR_AfGcW-BZM' 
    app = ApplicationBuilder().token(TOKEN).build()
    
    commands = [
        BotCommand("m", "بدء لعبة مافيا جديدة"),
        BotCommand("join", "انضمام للعبة الحالية"),
        BotCommand("go", "توزيع الأدوار وبدء الليل"),
        BotCommand("vote", "فتح استطلاع التصويت في الجروب")
    ]
    app.bot.set_my_commands(commands)
    
    app.add_handler(CommandHandler("m", mafia_command))
    app.add_handler(CommandHandler("join", join_command))
    app.add_handler(CommandHandler("go", go_command))
    app.add_handler(CommandHandler("vote", vote_command))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(PollAnswerHandler(handle_poll_answer))
    
    app.run_polling()

  
