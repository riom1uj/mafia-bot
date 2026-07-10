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

if __name__ == '__main__':
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
