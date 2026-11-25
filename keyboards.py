# -*- coding: utf-8 -*-
from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from config import SUBSCRIBE_CHANNELS

# ------------------------------------------------------------- USER MENU ---

USER_MENU = ReplyKeyboardMarkup(
    [
        ["✅ Test ishlashga tayyorman!"],
        ["📊 Mening natijalarim", "✏️ Ismni o'zgartirish"],
        ["👑 Admin bo'lish"],
    ],
    resize_keyboard=True,
)

ADMIN_MENU = ReplyKeyboardMarkup(
    [
        ["🧩 Test yaratish"],
        ["🚀 Start test"],
        ["🛑 Stop test", "👥 Faollar soni"],
        ["➕ Admin qo'shish", "📋 Testlarim"],
        ["📱 Foydalanuvchilar telefon raqami"],
        ["⬅️ Oddiy menyu"],
    ],
    resize_keyboard=True,
)

QUESTION_COLLECT_MENU = ReplyKeyboardMarkup(
    [["✅ Testni yakunlash"], ["❌ Bekor qilish"]],
    resize_keyboard=True,
)

CONTACT_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("📱 Kontaktni yuborish", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


def subscribe_keyboard():
    rows = [[InlineKeyboardButton(f"➡️ {c['title']}", url=c["url"])] for c in SUBSCRIBE_CHANNELS]
    rows.append([InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(rows)


def question_keyboard(q_index, options):
    letters = ["A", "B", "C", "D", "E", "F"]
    rows = []
    for i, opt in enumerate(options):
        rows.append([InlineKeyboardButton(f"{letters[i]}) {opt}", callback_data=f"ans:{q_index}:{i}")])
    return InlineKeyboardMarkup(rows)


def history_keyboard(history_items):
    rows = []
    for t in history_items[:15]:
        label = f"#{t['id']} — {t['started_at']} ({len(t['participants'])} ishtirokchi)"
        rows.append([InlineKeyboardButton(label, callback_data=f"hist:{t['id']}")])
    return InlineKeyboardMarkup(rows) if rows else None
