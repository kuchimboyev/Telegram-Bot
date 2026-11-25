# -*- coding: utf-8 -*-
"""
Oddiy JSON asosidagi ma'lumotlar bazasi.
Barcha holat (foydalanuvchilar, savollar, joriy test, tarix) shu yerda saqlanadi.
"""
import json
import os
import threading
from datetime import datetime

from config import DATA_FILE, INITIAL_ADMIN_IDS

_lock = threading.Lock()

_DEFAULT_DB = {
    "users": {},              # str(user_id) -> user dict
    "ready_users": [],        # test ishlashga tayyor bo'lganlar (joriy tur uchun)
    "pending_questions": [],  # admin hozir tuzayotgan savollar ro'yxati
    "current_test": None,     # faol test (dict) yoki None
    "history": [],            # tugagan testlar ro'yxati
    "next_test_id": 1,
}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                db = json.load(f)
            except json.JSONDecodeError:
                db = {}
    else:
        db = {}
    # yetishmayotgan kalitlarni to'ldiramiz
    for k, v in _DEFAULT_DB.items():
        if k not in db:
            db[k] = v if not isinstance(v, (dict, list)) else (dict(v) if isinstance(v, dict) else list(v))
    return db


DB = load_db()


def save_db():
    with _lock:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DB, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- USERS ----

def get_user(user_id):
    return DB["users"].get(str(user_id))


def upsert_user(tg_user, phone=None):
    uid = str(tg_user.id)
    existing = DB["users"].get(uid)
    is_admin = bool(existing and existing.get("is_admin")) or (tg_user.id in INITIAL_ADMIN_IDS)
    user = {
        "id": tg_user.id,
        "username": tg_user.username,
        "first_name": tg_user.first_name or "",
        "custom_name": existing.get("custom_name") if existing else None,
        "phone": phone if phone else (existing.get("phone") if existing else None),
        "is_admin": is_admin,
        "subscribed_ok": existing.get("subscribed_ok", False) if existing else False,
        "joined_at": existing.get("joined_at", _now()) if existing else _now(),
    }
    DB["users"][uid] = user
    save_db()
    return user


def set_subscribed(user_id, value=True):
    u = DB["users"].get(str(user_id))
    if u:
        u["subscribed_ok"] = value
        save_db()


def set_phone(user_id, phone):
    u = DB["users"].get(str(user_id))
    if u:
        u["phone"] = phone
        save_db()


def set_custom_name(user_id, name):
    u = DB["users"].get(str(user_id))
    if u:
        u["custom_name"] = name
        save_db()


def make_admin(user_id):
    u = DB["users"].get(str(user_id))
    if u:
        u["is_admin"] = True
        save_db()
        return True
    return False


def display_name(user_id):
    u = DB["users"].get(str(user_id))
    if not u:
        return f"ID:{user_id}"
    return u.get("custom_name") or u.get("first_name") or (f"@{u['username']}" if u.get("username") else f"ID:{user_id}")


def all_users():
    return list(DB["users"].values())


def is_admin(user_id):
    u = DB["users"].get(str(user_id))
    return bool(u and u.get("is_admin"))


# --------------------------------------------------------- READY USERS -----

def set_ready(user_id):
    if user_id not in DB["ready_users"]:
        DB["ready_users"].append(user_id)
        save_db()


def ready_count():
    return len(DB["ready_users"])


def clear_ready():
    DB["ready_users"] = []
    save_db()


def get_ready_users():
    return list(DB["ready_users"])


# ------------------------------------------------------- PENDING QUESTIONS -

def add_pending_questions(questions):
    DB["pending_questions"].extend(questions)
    save_db()


def get_pending_questions():
    return list(DB["pending_questions"])


def clear_pending_questions():
    DB["pending_questions"] = []
    save_db()


# ------------------------------------------------------------ CURRENT TEST -

def start_test(questions, participant_ids):
    test_id = DB["next_test_id"]
    DB["next_test_id"] = test_id + 1
    participants = {}
    for uid in participant_ids:
        participants[str(uid)] = {
            "name": display_name(uid),
            "score": 0,
            "answered": 0,
            "total_time": 0.0,
        }
    DB["current_test"] = {
        "id": test_id,
        "questions": questions,
        "participants": participants,
        "current_q_index": -1,
        "status": "running",
        "started_at": _now(),
        "finished_at": None,
    }
    save_db()
    return DB["current_test"]


def get_current_test():
    return DB["current_test"]


def record_answer(user_id, correct, time_taken):
    t = DB["current_test"]
    if not t:
        return
    p = t["participants"].get(str(user_id))
    if not p:
        return
    p["answered"] += 1
    p["total_time"] += time_taken
    if correct:
        p["score"] += 1
    save_db()


def advance_question(index):
    t = DB["current_test"]
    if t:
        t["current_q_index"] = index
        save_db()


def finish_test(status="finished"):
    t = DB["current_test"]
    if not t:
        return None
    t["status"] = status
    t["finished_at"] = _now()
    DB["history"].append(t)
    DB["current_test"] = None
    save_db()
    return t


def get_history():
    return list(reversed(DB["history"]))


def get_test_by_id(test_id):
    for t in DB["history"]:
        if t["id"] == test_id:
            return t
    return None


def get_last_result_for_user(user_id):
    for t in reversed(DB["history"]):
        if str(user_id) in t["participants"]:
            return t
    return None


def ranking_of(test):
    """Ishtirokchilarni: ko'p to'g'ri javob -> kam umumiy vaqt bo'yicha saralaydi."""
    items = list(test["participants"].items())
    items.sort(key=lambda kv: (-kv[1]["score"], kv[1]["total_time"]))
    return items
