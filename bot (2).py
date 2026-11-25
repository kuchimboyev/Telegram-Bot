# -*- coding: utf-8 -*-
import asyncio
import logging
import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import config
import storage
from quiz_parser import parse_questions, ParseError
from keyboards import (
    USER_MENU,
    ADMIN_MENU,
    QUESTION_COLLECT_MENU,
    CONTACT_KEYBOARD,
    subscribe_keyboard,
    question_keyboard,
    history_keyboard,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger("quizbot")

# Runtime (persistlanmaydigan, faqat dastur ishlab turgan paytda kerak) holat
RUNTIME = {
    "running": False,
    "stop_requested": False,
    "question_sent_at": {},
    "message_ids": {},
    "answered_users": {},
}


# ============================================================ YORDAMCHI ====

async def check_subscription(bot, user_id: int) -> bool:
    if not config.SUBSCRIBE_CHANNELS:
        return True
    for ch in config.SUBSCRIBE_CHANNELS:
        try:
            member = await bot.get_chat_member(ch["id"], user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception as e:
            log.warning("Obunani tekshirishda xato (%s): %s", ch["id"], e)
            return False
    return True


async def show_main_menu(bot, chat_id, user_id):
    if storage.is_admin(user_id):
        await bot.send_message(chat_id, "🛠 Admin paneli:", reply_markup=ADMIN_MENU)
    else:
        await bot.send_message(chat_id, "📋 Asosiy menyu:", reply_markup=USER_MENU)


async def send_welcome(bot, chat_id, user):
    name = user.first_name or (f"@{user.username}" if user.username else "do'stim")
    text = (
        f"Assalomu alaykum {name}, botga hush kelibsiz!\n"
        f"Siz @kuchimboyev tomonidan yaratilgan botda o'z bilimingizni sinab ko'rmoqdasiz."
    )
    await bot.send_message(chat_id, text)
    u = storage.get_user(user.id)
    if not u or not u.get("phone"):
        await bot.send_message(
            chat_id,
            "Davom etish uchun kontakt ma'lumotingizni yuboring 👇",
            reply_markup=CONTACT_KEYBOARD,
        )
    else:
        await show_main_menu(bot, chat_id, user.id)


def chunk_text(lines, limit=3500):
    chunks = []
    cur = ""
    for line in lines:
        if len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = ""
        cur += line + "\n"
    if cur:
        chunks.append(cur)
    return chunks


# =============================================================== /start ====

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    storage.upsert_user(user)
    context.user_data.pop("state", None)

    ok = await check_subscription(context.bot, user.id)
    if not ok:
        await update.message.reply_text(
            "Botdan foydalanish uchun avval quyidagi kanal(lar)ga obuna bo'ling, "
            "so'ng \"✅ Obunani tekshirish\" tugmasini bosing:",
            reply_markup=subscribe_keyboard(),
        )
        return

    storage.set_subscribed(user.id, True)
    await send_welcome(context.bot, update.effective_chat.id, user)


async def on_check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    ok = await check_subscription(context.bot, user.id)
    if not ok:
        await query.answer("❌ Siz hali barcha kanallarga obuna bo'lmagansiz.", show_alert=True)
        return
    storage.set_subscribed(user.id, True)
    await query.answer("✅ Obuna tasdiqlandi!")
    try:
        await query.edit_message_text("✅ Obuna tasdiqlandi!")
    except Exception:
        pass
    await send_welcome(context.bot, query.message.chat_id, user)


async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user
    if contact.user_id and contact.user_id != user.id:
        await update.message.reply_text("Iltimos, faqat OʻZINGIZNING kontaktingizni yuboring.")
        return
    storage.set_phone(user.id, contact.phone_number)
    await update.message.reply_text("✅ Rahmat!")
    await show_main_menu(context.bot, update.effective_chat.id, user.id)


# ======================================================== ADMIN: TEST ======

async def cmd_create_test(update, context, user_id):
    if storage.get_current_test():
        await update.message.reply_text("⚠️ Hozir faol test davom etmoqda. Avval uni to'xtating.")
        return
    storage.clear_pending_questions()
    context.user_data["state"] = "collecting_questions"
    await update.message.reply_text(
        "✍️ Savollarni quyidagi formatda yuboring (bitta yoki bir nechtasini bo'sh qator bilan ajratib):\n\n"
        "Oʻzbekiston qachon mustaqillikka erishgan?\n"
        "A) 1990\nB) 1991\nC) 1992\nD) 1993\n"
        "Javob: B\n\n"
        "Tugatgach \"✅ Testni yakunlash\" tugmasini bosing.",
        reply_markup=QUESTION_COLLECT_MENU,
    )


async def cmd_start_test(update, context, user_id):
    if storage.get_current_test():
        await update.message.reply_text("⚠️ Test allaqachon ishga tushirilgan.")
        return
    questions = storage.get_pending_questions()
    if not questions:
        await update.message.reply_text("⚠️ Avval \"🧩 Test yaratish\" orqali savollar tayyorlang.")
        return
    participants = storage.get_ready_users()
    if not participants:
        await update.message.reply_text(
            "⚠️ Hozircha hech kim \"Test ishlashga tayyorman!\" tugmasini bosmagan."
        )
        return

    test = storage.start_test(questions, participants)
    storage.clear_pending_questions()
    storage.clear_ready()
    RUNTIME["stop_requested"] = False
    RUNTIME["running"] = True

    await update.message.reply_text(
        f"🚀 Test boshlandi!\n📄 Savollar soni: {len(questions)}\n👥 Ishtirokchilar: {len(participants)}"
    )
    asyncio.create_task(run_test(context.application, test["id"]))


async def cmd_stop_test(update, context, user_id):
    if not storage.get_current_test():
        await update.message.reply_text("Hozir faol test yo'q.")
        return
    RUNTIME["stop_requested"] = True
    await update.message.reply_text("🛑 Test to'xtatilmoqda...")


async def run_test(application: Application, test_id: int):
    bot = application.bot
    test = storage.get_current_test()
    if not test:
        return
    questions = test["questions"]
    participant_ids = [int(uid) for uid in test["participants"].keys()]

    for idx, q in enumerate(questions):
        if RUNTIME["stop_requested"]:
            break
        storage.advance_question(idx)
        RUNTIME["question_sent_at"][idx] = time.time()
        RUNTIME["answered_users"][idx] = set()
        RUNTIME["message_ids"][idx] = {}

        text = f"❓ {idx + 1}-savol / {len(questions)}\n\n{q['text']}"
        kb = question_keyboard(idx, q["options"])
        for uid in participant_ids:
            try:
                msg = await bot.send_message(uid, text, reply_markup=kb)
                RUNTIME["message_ids"][idx][uid] = msg.message_id
            except Exception as e:
                log.warning("Savol yuborilmadi (%s): %s", uid, e)

        waited = 0
        while waited < config.QUESTION_TIME_SECONDS:
            if RUNTIME["stop_requested"]:
                break
            await asyncio.sleep(1)
            waited += 1

        for uid, mid in RUNTIME["message_ids"].get(idx, {}).items():
            if uid not in RUNTIME["answered_users"].get(idx, set()):
                try:
                    await bot.edit_message_reply_markup(uid, mid, reply_markup=None)
                except Exception:
                    pass

        if RUNTIME["stop_requested"]:
            break

    status = "stopped" if RUNTIME["stop_requested"] else "finished"
    finished_test = storage.finish_test(status)
    RUNTIME["stop_requested"] = False
    RUNTIME["running"] = False

    if finished_test:
        await announce_results(bot, finished_test)


async def announce_results(bot, test):
    ranking = storage.ranking_of(test)
    for uid_str, _ in ranking:
        try:
            await bot.send_message(
                int(uid_str),
                "🏁 Test yakunlandi! Natijangizni \"📊 Mening natijalarim\" tugmasi orqali ko'rishingiz mumkin.",
            )
        except Exception:
            pass

    lines = [f"🏁 Test #{test['id']} yakunlandi.\n📄 Savollar: {len(test['questions'])}\n👥 Ishtirokchilar: {len(ranking)}\n"]
    for i, (uid_str, p) in enumerate(ranking, start=1):
        lines.append(f"{i}. {p['name']} — {p['score']} ta to'g'ri")
    result_text = "\n".join(lines) if ranking else "Ishtirokchilar bo'lmadi."

    for u in storage.all_users():
        if u.get("is_admin"):
            try:
                await bot.send_message(u["id"], result_text)
            except Exception:
                pass


async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    try:
        _, qidx_s, optidx_s = query.data.split(":")
        qidx, optidx = int(qidx_s), int(optidx_s)
    except Exception:
        await query.answer()
        return

    test = storage.get_current_test()
    if not test or test.get("current_q_index") != qidx:
        await query.answer("⏱ Bu savol vaqti tugagan.", show_alert=True)
        return
    if str(user_id) not in test["participants"]:
        await query.answer("Siz bu testda ishtirok etmayapsiz.", show_alert=True)
        return
    if user_id in RUNTIME["answered_users"].get(qidx, set()):
        await query.answer("Siz allaqachon javob bergansiz.", show_alert=True)
        return

    RUNTIME["answered_users"].setdefault(qidx, set()).add(user_id)
    q = test["questions"][qidx]
    correct = optidx == q["correct"]
    sent_at = RUNTIME["question_sent_at"].get(qidx, time.time())
    time_taken = max(0.0, time.time() - sent_at)
    storage.record_answer(user_id, correct, time_taken)

    await query.answer("✅ To'g'ri javob!" if correct else "❌ Noto'g'ri javob.")
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass


# ======================================================== ADMIN: BOSHQA ====

async def cmd_active_count(update, context, user_id):
    total = len(storage.all_users())
    ready = storage.ready_count()
    await update.message.reply_text(
        f"👥 Botdagi jami foydalanuvchilar: {total}\n✅ \"Tayyorman\" deganlar: {ready}"
    )


async def cmd_ask_add_admin(update, context, user_id):
    context.user_data["state"] = "awaiting_admin_target"
    await update.message.reply_text(
        "Yangi admin qilmoqchi bo'lgan foydalanuvchining Telegram ID raqamini yoki @username'ini yuboring.\n"
        "(U foydalanuvchi avval botga /start bosgan bo'lishi shart.)"
    )


async def handle_add_admin_target(update, context, text):
    text = text.strip().lstrip("@")
    target = None
    if text.isdigit():
        target = storage.get_user(int(text))
    else:
        for u in storage.all_users():
            if u.get("username") and u["username"].lower() == text.lower():
                target = u
                break
    context.user_data.pop("state", None)
    if not target:
        await update.message.reply_text(
            "❌ Bunday foydalanuvchi topilmadi. U avval botga /start bosgan bo'lishi kerak."
        )
        return
    storage.make_admin(target["id"])
    await update.message.reply_text(
        f"✅ {storage.display_name(target['id'])} endi admin!"
    )
    try:
        await context.bot.send_message(target["id"], "🎉 Sizga admin huquqi berildi!")
        await show_main_menu(context.bot, target["id"], target["id"])
    except Exception:
        pass


async def cmd_my_tests(update, context, user_id):
    history = storage.get_history()
    if not history:
        await update.message.reply_text("Hali birorta test tugallanmagan.")
        return
    await update.message.reply_text(
        "📋 Testlar tarixi (birini tanlang):", reply_markup=history_keyboard(history)
    )


async def on_history_pick(update, context):
    query = update.callback_query
    if not storage.is_admin(query.from_user.id):
        await query.answer()
        return
    test_id = int(query.data.split(":")[1])
    test = storage.get_test_by_id(test_id)
    if not test:
        await query.answer("Topilmadi.", show_alert=True)
        return
    await query.answer()
    ranking = storage.ranking_of(test)
    lines = [f"📋 Test #{test['id']} — {test['started_at']}\n📄 Savollar: {len(test['questions'])}\n"]
    for i, (uid_str, p) in enumerate(ranking, start=1):
        lines.append(f"{i}. {p['name']} — {p['score']}/{len(test['questions'])} to'g'ri")
    for chunk in chunk_text(lines):
        await query.message.reply_text(chunk)


async def cmd_phone_list(update, context, user_id):
    users_with_phone = [u for u in storage.all_users() if u.get("phone")]
    if not users_with_phone:
        await update.message.reply_text("Hozircha hech kimning raqami yo'q.")
        return
    lines = []
    for u in users_with_phone:
        uname = f"@{u['username']}" if u.get("username") else storage.display_name(u["id"])
        lines.append(f"{uname} — {u['phone']}")
    await update.message.reply_text(f"📱 Jami: {len(lines)} ta raqam\n")
    for chunk in chunk_text(lines):
        await update.message.reply_text(chunk)


# ========================================================= FOYDALANUVCHI ===

async def cmd_ready(update, context, user_id):
    if storage.get_current_test():
        await update.message.reply_text("⏳ Hozir test davom etmoqda, keyingi safar ulanishga ulguring.")
        return
    storage.set_ready(user_id)
    await update.message.reply_text("✅ Siz ro'yxatga qo'shildingiz! Test boshlanishini kuting.")


async def cmd_my_results(update, context, user_id):
    test = storage.get_last_result_for_user(user_id)
    if not test:
        await update.message.reply_text("Siz hali birorta testda ishtirok etmagansiz.")
        return
    ranking = storage.ranking_of(test)
    position = next((i for i, (uid, _) in enumerate(ranking, start=1) if uid == str(user_id)), None)
    p = test["participants"][str(user_id)]
    await update.message.reply_text(
        f"🗓 Test #{test['id']} ({test['started_at']})\n"
        f"🏆 To'g'ri javoblar: {p['score']}/{len(test['questions'])}\n"
        f"📍 Sizning o'rningiz: {position}/{len(ranking)}"
    )


async def cmd_ask_new_name(update, context, user_id):
    context.user_data["state"] = "awaiting_new_name"
    await update.message.reply_text("✏️ Yangi ismingizni kiriting:")


async def handle_new_name(update, context, text, user_id):
    name = text.strip()[:50]
    if not name:
        await update.message.reply_text("Ism bo'sh bo'lishi mumkin emas, qaytadan kiriting:")
        return
    storage.set_custom_name(user_id, name)
    context.user_data.pop("state", None)
    await update.message.reply_text(f"✅ Ismingiz o'zgartirildi: {name}")


async def cmd_become_admin_request(update, context, user_id):
    user = update.effective_user
    admins = [u for u in storage.all_users() if u.get("is_admin")]
    username_line = f"Username: @{user.username}" if user.username else "Username: -"
    info = (
        f"👑 Foydalanuvchi admin bo'lishni so'ramoqda:\n"
        f"Ism: {storage.display_name(user_id)}\n"
        f"{username_line}\n"
        f"ID: {user_id}\n\n"
        f"\"➕ Admin qo'shish\" orqali shu ID/username'ni yuboring."
    )
    for a in admins:
        try:
            await context.bot.send_message(a["id"], info)
        except Exception:
            pass
    await update.message.reply_text("✅ So'rovingiz adminlarga yuborildi.")


# ============================================================= ROUTER ======

TEXT_ROUTES_ADMIN = {
    "🧩 Test yaratish": cmd_create_test,
    "🚀 Start test": cmd_start_test,
    "🛑 Stop test": cmd_stop_test,
    "👥 Faollar soni": cmd_active_count,
    "➕ Admin qo'shish": cmd_ask_add_admin,
    "📋 Testlarim": cmd_my_tests,
    "📱 Foydalanuvchilar telefon raqami": cmd_phone_list,
}

TEXT_ROUTES_USER = {
    "✅ Test ishlashga tayyorman!": cmd_ready,
    "📊 Mening natijalarim": cmd_my_results,
    "👑 Admin bo'lish": cmd_become_admin_request,
}


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    state = context.user_data.get("state")

    # -------- ko'p bosqichli holatlar --------
    if state == "collecting_questions":
        if text == "✅ Testni yakunlash":
            count = len(storage.get_pending_questions())
            context.user_data.pop("state", None)
            if count == 0:
                await update.message.reply_text("⚠️ Birorta ham savol qo'shilmadi.", reply_markup=ADMIN_MENU)
            else:
                await update.message.reply_text(
                    f"✅ Test tayyor! Jami {count} ta savol qabul qilindi.\n"
                    f"Boshlash uchun \"🚀 Start test\" tugmasini bosing.",
                    reply_markup=ADMIN_MENU,
                )
            return
        if text == "❌ Bekor qilish":
            storage.clear_pending_questions()
            context.user_data.pop("state", None)
            await update.message.reply_text("Bekor qilindi.", reply_markup=ADMIN_MENU)
            return
        try:
            questions = parse_questions(text)
        except ParseError as e:
            await update.message.reply_text(f"❌ Xatolik:\n{e}")
            return
        storage.add_pending_questions(questions)
        total = len(storage.get_pending_questions())
        await update.message.reply_text(
            f"✅ {len(questions)} ta savol qabul qilindi. Jami: {total} ta.\n"
            f"Davom eting yoki \"✅ Testni yakunlash\" tugmasini bosing."
        )
        return

    if state == "awaiting_admin_target":
        await handle_add_admin_target(update, context, text)
        return

    if state == "awaiting_new_name":
        await handle_new_name(update, context, text, user.id)
        return

    # -------- oddiy tugmalar --------
    if text == "⬅️ Oddiy menyu":
        await update.message.reply_text("📋 Asosiy menyu:", reply_markup=USER_MENU)
        return

    if storage.is_admin(user.id) and text in TEXT_ROUTES_ADMIN:
        await TEXT_ROUTES_ADMIN[text](update, context, user.id)
        return

    if text in TEXT_ROUTES_USER:
        await TEXT_ROUTES_USER[text](update, context, user.id)
        return

    await update.message.reply_text(
        "Iltimos, pastdagi tugmalardan birini tanlang. /start bosib menyuni qayta yuklashingiz mumkin."
    )


# =============================================================== MAIN ======

def main():
    if config.BOT_TOKEN == "SIZNING_BOT_TOKENINGIZ":
        raise SystemExit(
            "❌ config.py faylida BOT_TOKEN ni to'ldirmagansiz! @BotFather dan token oling."
        )

    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.CONTACT, on_contact))
    app.add_handler(CallbackQueryHandler(on_check_sub, pattern=r"^check_sub$"))
    app.add_handler(CallbackQueryHandler(on_answer, pattern=r"^ans:"))
    app.add_handler(CallbackQueryHandler(on_history_pick, pattern=r"^hist:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    log.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
