# -*- coding: utf-8 -*-
"""
Bot sozlamalari.
Maxfiy ma'lumot (BOT_TOKEN) ushbu fayl ichida emas, balki ".env" faylida saqlanadi.
Terminalda ishga tushirishdan oldin ".env" faylini to'ldiring (pastga qarang).
"""
import os
from dotenv import load_dotenv

load_dotenv()  # ".env" faylini o'qib, muhit o'zgaruvchilariga yuklaydi

# 1) BotFather dan olingan token — ".env" faylidan o'qiladi
BOT_TOKEN = os.getenv("BOT_TOKEN", "SIZNING_BOT_TOKENINGIZ")

# 2) Botni ilk marta ishga tushirganda admin bo'ladigan Telegram ID(lar).
#    ".env" faylida "ADMIN_IDS=5734785343,111111111" ko'rinishida, vergul bilan ajratib yozing.
#    O'z Telegram ID'ingizni bilish uchun @userinfobot ga /start bosing.
_admin_ids_raw = os.getenv("ADMIN_IDS", "5734785343")
INITIAL_ADMIN_IDS = [int(x) for x in _admin_ids_raw.split(",") if x.strip().isdigit()]

# 3) Majburiy obuna kanallari.
#    - Bot shu kanal(lar)ga ADMIN qilib qo'shilishi SHART (a'zolikni tekshirish uchun).
#    - "id" — kanalning @username'i
#    - "title" — foydalanuvchiga ko'rsatiladigan nom
#    - "url" — kanalga o'tish havolasi (obuna bo'ling tugmasi uchun)
#    Agar majburiy obuna kerak bo'lmasa, ro'yxatni bo'sh qoldiring: SUBSCRIBE_CHANNELS = []
SUBSCRIBE_CHANNELS = [
    {"id": "@kuchimboyev7", "title": "Kuchimboyev kanali", "url": "https://t.me/kuchimboyev7"},
]

# 4) Har bir savolga beriladigan vaqt (soniyada)
QUESTION_TIME_SECONDS = 25

# 5) Ma'lumotlar saqlanadigan fayl (o'zgartirish shart emas)
DATA_FILE = "data.json"
