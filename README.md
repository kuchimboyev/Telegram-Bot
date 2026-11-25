# 📚 Test Bot — Telegram

O'quvchilar uchun sinfda bir vaqtda ishlaydigan test-bot. Admin savollarni matn
shaklida yuboradi, bot ularni tushunib, testni belgilangan vaqt bo'yicha
avtomatik boshqaradi.

## 1. O'rnatish

```bash
cd quizbot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Sozlash (`.env` va `config.py`)

Maxfiy ma'lumotlar (token, admin ID) `.env` faylida saqlanadi — bu fayl kodning qolgan qismidan alohida turadi va hech qachon boshqalarga ulashilmasligi kerak.

`.env` fayli (allaqachon to'ldirilgan holda berilgan):
```
BOT_TOKEN=SIZNING_TOKENINGIZ
ADMIN_IDS=5734785343
```
- Bir nechta admin qo'shmoqchi bo'lsangiz: `ADMIN_IDS=5734785343,111111111` (vergul bilan).
- **`.env` faylini hech qachon boshqalarga yubormang yoki GitHub'ga ochiq holda yuklamang** — u sizning botingizni to'liq boshqarish huquqini beradi. Agar token oshkor bo'lib qolgan bo'lsa, @BotFather orqali `/revoke` bilan uni bekor qilib, yangisini oling.
- `.env.example` — bu namunaviy fayl, haqiqiy tokensiz; boshqa birov bilan kodni bo'lishganingizda shuni ulashing.

`config.py` faylida esa faqat texnik sozlamalar qoladi:
- **SUBSCRIBE_CHANNELS** — majburiy obuna bo'lish kerak bo'lgan kanal(lar). **Muhim: botni o'sha kanal(lar)ga ADMIN qilib qo'shing**, aks holda obunani tekshira olmaydi. Agar majburiy obuna kerak bo'lmasa, ro'yxatni bo'sh qoldiring: `SUBSCRIBE_CHANNELS = []`.
- **QUESTION_TIME_SECONDS** — har bir savolga beriladigan vaqt (soniyada), standart 25.

## 3. Ishga tushirish

```bash
python bot.py
```

Terminalda `Bot ishga tushdi...` degan yozuv chiqsa — bot ishlayapti. To'xtatish uchun `Ctrl+C`.

## 4. Botdan foydalanish

### O'quvchi tomonidan
1. Botga `/start` bosadi.
2. Kerak bo'lsa, kanalga obuna bo'lib, "✅ Obunani tekshirish" tugmasini bosadi.
3. Kontakt ma'lumotini yuboradi.
4. Menyu chiqadi: **Test ishlashga tayyorman!**, **Mening natijalarim**, **Ismni o'zgartirish**, **Admin bo'lish**.

### Admin tomonidan
1. `INITIAL_ADMIN_IDS` ichida bo'lgan foydalanuvchi botga `/start` bosganda avtomatik admin paneli chiqadi.
2. **🧩 Test yaratish** — bot savol formatini so'raydi. Har bir savolni quyidagicha yuboring:

   ```
   Oʻzbekiston qachon mustaqillikka erishgan?
   A) 1990
   B) 1991
   C) 1992
   D) 1993
   Javob: B
   ```

   Bir nechta savolni bitta xabarda, orasiga **bo'sh qator** qo'yib ham yuborish mumkin:

   ```
   Poytaxtimiz qaysi shahar?
   A) Samarqand
   B) Buxoro
   C) Toshkent
   D) Andijon
   Javob: C

   Eng katta okean qaysi?
   A) Atlantika
   B) Tinch okeani
   C) Hind okeani
   D) Shimoliy Muz okeani
   Javob: B
   ```

   Savol qo'shishni tugatgach **✅ Testni yakunlash** tugmasini bosing.

3. **🚀 Start test** — "✅ Test ishlashga tayyorman!" tugmasini bosgan barcha o'quvchilarga savollar birma-bir, belgilangan vaqt bilan yuboriladi. Har bir savol ostida A/B/C/D tugmalari chiqadi.
4. **🛑 Stop test** — testni istalgan vaqtda to'xtatadi, natijalar shu paytgacha hisoblanadi.
5. **👥 Faollar soni** — botdagi jami foydalanuvchilar va "tayyorman" deganlar sonini ko'rsatadi.
6. **➕ Admin qo'shish** — foydalanuvchi ID yoki @username'ini yuboring (u avval botga `/start` bosgan bo'lishi shart).
7. **📋 Testlarim** — o'tgan testlar ro'yxati va har birining to'liq reytingi.
8. **📱 Foydalanuvchilar telefon raqami** — kontakt yuborgan barcha foydalanuvchilar ro'yxati.

## 5. Muhim eslatmalar

- Ma'lumotlar `data.json` faylida saqlanadi — botni qayta ishga tushirsangiz ham foydalanuvchilar, tarix va adminlar saqlanib qoladi.
- Test **butun sinf uchun sinxron** boradi: hamma bir xil savolni bir vaqtda ko'radi, vaqt tugagach hammaga birgalikda keyingi savol yuboriladi.
- Bitta vaqtning o'zida faqat **bitta** test faol bo'lishi mumkin.
- Reyting: ko'proq to'g'ri javob bergan yuqorida turadi; teng bo'lsa, tezroq javob bergan (umumiy sarflangan vaqti kamroq) yuqori chiqadi.
- Botni doim ishlab turishini xohlasangiz (kompyuter o'chganda ham), keyinchalik uni server yoki VPS'ga joylashtirish kerak bo'ladi — hozircha terminalda ishga tushirilgan vaqtda ishlaydi.
