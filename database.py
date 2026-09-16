import os
os.makedirs("/app/data", exist_ok=True)
os.chdir("/app/data")

import sqlite3
from datetime import datetime, date


def init_db():
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        gender TEXT,
        age INTEGER,
        height INTEGER,
        start_weight REAL,
        current_weight REAL,
        goal_weight REAL,
        activity TEXT,
        daily_calories INTEGER,
        daily_water INTEGER DEFAULT 2500,
        created_at TEXT
    )""")

    # Добавляем новые колонки (миграция)
    for col, default in [
        ("water_hours", "'10,13,16,19,22'"),
        ("weigh_hour", "8"),
        ("remind_water", "1"),
        ("remind_weigh", "1"),
    ]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT {default}")
        except:
            pass

    c.execute("""CREATE TABLE IF NOT EXISTS water (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, date TEXT, ml INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, date TEXT, weight REAL,
        weigh_type TEXT DEFAULT 'fasted'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, date TEXT,
        neck REAL, chest REAL, waist REAL, hips REAL, arm REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS dishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_type TEXT, name TEXT,
        base_calories REAL, base_protein REAL, base_fat REAL,
        base_carbs REAL, base_weight REAL, ingredients TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS food_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, date TEXT, meal_type TEXT, food_name TEXT,
        grams REAL, calories REAL, protein REAL, fat REAL, carbs REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_foods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, name TEXT,
        per100_cal REAL, per100_prot REAL, per100_fat REAL, per100_carb REAL
    )""")

    try:
        c.execute("ALTER TABLE weights ADD COLUMN weigh_type TEXT DEFAULT 'fasted'")
    except:
        pass

    conn.commit()
    conn.close()


def get_user(uid):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = ["user_id","username","gender","age","height","start_weight","current_weight",
            "goal_weight","activity","daily_calories","daily_water","created_at",
            "water_hours","weigh_hour","remind_water","remind_weigh"]
    return dict(zip(keys, row[:15]))


def create_user(uid, data):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO users
        (user_id, username, gender, age, height, start_weight, current_weight,
         goal_weight, activity, daily_calories, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (uid, data.get("username"), data["gender"], data["age"], data["height"],
         data["start_weight"], data["start_weight"], data["goal_weight"],
         data["activity"], data["daily_calories"], datetime.now().isoformat()))
    conn.commit()
    conn.close()


def update_user(uid, field, value):
    allowed = {"water_hours", "weigh_hour", "remind_water", "remind_weigh",
               "current_weight", "daily_water"}
    if field not in allowed:
        return False
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, uid))
    conn.commit()
    conn.close()
    return True


def get_all_users():
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""SELECT user_id, water_hours, weigh_hour, remind_water, remind_weigh
                 FROM users""")
    rows = c.fetchall()
    conn.close()
    return [
        {"user_id": r[0], "water_hours": r[1] or "10,13,16,19,22",
         "weigh_hour": int(r[2]) if r[2] else 8,
         "remind_water": int(r[3]) if r[3] else 0,
         "remind_weigh": int(r[4]) if r[4] else 0}
        for r in rows
    ]


def add_water(uid, ml):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("INSERT INTO water (user_id, date, ml) VALUES (?,?,?)",
              (uid, date.today().isoformat(), ml))
    conn.commit()
    conn.close()


def get_water_today(uid):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(ml),0) FROM water WHERE user_id=? AND date=?",
              (uid, date.today().isoformat()))
    total = c.fetchone()[0]
    conn.close()
    return total


def add_weight(uid, weight, weigh_type="fasted"):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute("DELETE FROM weights WHERE user_id=? AND date=? AND weigh_type=?",
              (uid, today, weigh_type))
    c.execute("INSERT INTO weights (user_id, date, weight, weigh_type) VALUES (?,?,?,?)",
              (uid, today, weight, weigh_type))
    if weigh_type == "fasted":
        c.execute("UPDATE users SET current_weight=? WHERE user_id=?", (weight, uid))
    conn.commit()
    conn.close()


def get_weights(uid, weigh_type="fasted", limit=90):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""SELECT date, weight FROM weights
                 WHERE user_id=? AND weigh_type=?
                 ORDER BY date DESC LIMIT ?""", (uid, weigh_type, limit))
    rows = c.fetchall()
    conn.close()
    return list(reversed(rows))


def get_last_weight(uid, weigh_type="fed"):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""SELECT date, weight FROM weights
                 WHERE user_id=? AND weigh_type=?
                 ORDER BY id DESC LIMIT 1""", (uid, weigh_type))
    row = c.fetchone()
    conn.close()
    return row


def add_measurement(uid, neck, chest, waist, hips, arm):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""INSERT INTO measurements (user_id, date, neck, chest, waist, hips, arm)
                 VALUES (?,?,?,?,?,?,?)""",
              (uid, date.today().isoformat(), neck, chest, waist, hips, arm))
    conn.commit()
    conn.close()


# ===== БЛЮДА (простые, без масел) =====

DISHES_DATA = [
    # === ЗАВТРАКИ ===
    ("breakfast", "Овсянка на молоке с бананом", 350, 12, 7, 58, 350,
     "Овсянка 60г, Молоко 200мл, Банан 1шт"),
    ("breakfast", "Овсянка на воде с яблоком", 260, 8, 4, 48, 350,
     "Овсянка 60г, Вода 250мл, Яблоко 1шт, Корица"),
    ("breakfast", "Яичница из 2 яиц с помидором", 260, 14, 17, 6, 200,
     "Яйца 2шт, Помидор 1шт (антипригарная сковорода)"),
    ("breakfast", "Омлет из 2 яиц с молоком", 240, 16, 15, 4, 200,
     "Яйца 2шт, Молоко 50мл (антипригарная сковорода)"),
    ("breakfast", "Творог 5% с мёдом", 280, 28, 10, 18, 220,
     "Творог 5% 180г, Мёд 1ч.л."),
    ("breakfast", "Творог 5% с ягодами", 250, 28, 9, 14, 250,
     "Творог 5% 180г, Ягоды 80г"),
    ("breakfast", "Сырники в духовке", 340, 24, 10, 38, 250,
     "Творог 5% 200г, Яйцо 1шт, Мука 30г, Сахар 1ч.л."),
    ("breakfast", "Гречневая каша на молоке", 340, 12, 8, 56, 350,
     "Гречка 60г, Молоко 200мл"),
    ("breakfast", "Рисовая каша на молоке", 330, 9, 7, 58, 350,
     "Рис 60г, Молоко 200мл, Сахар 1ч.л."),
    ("breakfast", "Пшённая каша с тыквой", 320, 9, 6, 58, 350,
     "Пшёнка 60г, Молоко 200мл, Тыква 100г"),
    ("breakfast", "Бутерброд с сыром", 290, 14, 12, 32, 180,
     "Хлеб 60г, Сыр 40г, Огурец 50г"),
    ("breakfast", "Йогурт натуральный с гранолой", 290, 14, 8, 40, 220,
     "Йогурт 3.2% 150г, Гранола 40г"),

    # === ОБЕДЫ ===
    ("lunch", "Борщ со сметаной", 350, 15, 12, 45, 500,
     "Борщ 400мл, Сметана 10% 30г, Хлеб 30г"),
    ("lunch", "Щи из свежей капусты", 280, 12, 8, 38, 500,
     "Щи 400мл, Хлеб 30г"),
    ("lunch", "Куриный суп с вермишелью", 320, 18, 8, 42, 500,
     "Суп 450мл, Курица 80г, Вермишель 30г, Хлеб 20г"),
    ("lunch", "Курица с гречкой", 430, 40, 8, 50, 400,
     "Куриное филе 150г (варёное), Гречка 80г (сухая)"),
    ("lunch", "Курица с рисом", 440, 38, 8, 55, 400,
     "Куриное филе 150г (варёное), Рис 80г (сухой)"),
    ("lunch", "Курица с макаронами", 470, 36, 8, 62, 400,
     "Куриное филе 150г, Макароны 80г (сухие)"),
    ("lunch", "Котлеты с пюре", 480, 30, 16, 52, 420,
     "Котлеты (говядина+свинина) 150г, Картофель 250г, Молоко 50мл"),
    ("lunch", "Плов с курицей", 490, 32, 12, 60, 450,
     "Рис 80г, Курица 130г, Морковь 80г, Лук 50г"),
    ("lunch", "Тушёная картошка с мясом", 460, 28, 14, 54, 450,
     "Картофель 250г, Говядина 130г, Морковь 50г, Лук 30г"),
    ("lunch", "Макароны по-флотски", 480, 26, 12, 62, 400,
     "Макароны 80г, Фарш 130г, Лук 50г"),
    ("lunch", "Рыбные котлеты с рисом", 420, 32, 10, 50, 420,
     "Котлеты из минтая 150г, Рис 70г, Яйцо 1шт, Лук 30г"),
    ("lunch", "Солянка", 380, 22, 14, 38, 500,
     "Солянка 450мл, Хлеб 30г"),
    ("lunch", "Голубцы с мясом", 400, 24, 14, 42, 400,
     "Капуста 200г, Фарш 120г, Рис 50г, Томат 50г"),
    ("lunch", "Пельмени отварные", 490, 22, 20, 55, 300,
     "Пельмени 250г, Сметана 10% 30г"),

    # === УЖИНЫ ===
    ("dinner", "Творог 5% со сметаной", 260, 30, 10, 12, 240,
     "Творог 5% 180г, Сметана 10% 50г"),
    ("dinner", "Кефир с отрубями", 180, 10, 6, 22, 300,
     "Кефир 1% 250мл, Отруби 20г"),
    ("dinner", "Запечённая курица с овощами", 350, 38, 10, 24, 400,
     "Куриное филе 180г (в фольге), Овощи 200г"),
    ("dinner", "Тушёная курица с кабачком", 320, 36, 8, 22, 400,
     "Курица 180г, Кабачок 200г, Лук 50г (тушить с водой)"),
    ("dinner", "Куриное филе с салатом", 280, 38, 5, 16, 400,
     "Куриное филе 180г (варёное), Салат 150г, Огурец 80г"),
    ("dinner", "Запечённая треска", 300, 40, 8, 18, 400,
     "Треска 200г (в фольге), Кабачок 150г, Перец 100г"),
    ("dinner", "Салат овощной с курицей", 300, 30, 8, 22, 400,
     "Курица 150г, Салат 100г, Огурец 80г, Помидор 80г, Сметана 10% 30г"),
    ("dinner", "Салат из огурцов и помидоров", 120, 3, 6, 14, 300,
     "Огурец 150г, Помидор 150г, Сметана 10% 30г, Зелень"),
    ("dinner", "Запеканка творожная", 350, 30, 10, 32, 320,
     "Творог 5% 200г, Яйцо 1шт, Овсянка 30г, Мёд 1ч.л."),
    ("dinner", "Гречка с кефиром", 280, 14, 6, 42, 350,
     "Гречка 60г (сухая), Кефир 1% 200мл"),
    ("dinner", "Овощное рагу", 240, 8, 6, 38, 400,
     "Кабачок 150г, Картофель 100г, Морковь 80г, Лук 50г, Томат 50г"),
    ("dinner", "Омлет с овощами", 280, 18, 14, 14, 300,
     "Яйца 2шт, Помидор 1шт, Перец 80г (антипригарная сковорода)"),
    ("dinner", "Индейка тушёная с овощами", 320, 34, 8, 26, 400,
     "Индейка 180г, Овощи 200г (тушить с водой)"),
    ("dinner", "Тушёная капуста с курицей", 300, 32, 8, 24, 400,
     "Капуста 250г, Курица 150г, Лук 50г, Морковь 50г"),
    ("dinner", "Творог с кефиром", 220, 28, 6, 14, 300,
     "Творог 5% 150г, Кефир 1% 150мл"),
]


def init_dishes():
    """Пересоздаёт блюда, если найден старый формат или нужны обновления."""
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()

    need_rebuild = False
    try:
        c.execute("SELECT COUNT(*) FROM dishes")
        if c.fetchone()[0] == 0:
            need_rebuild = True
        else:
            # Признак старых рецептов — наличие масла или сложных блюд
            c.execute("""SELECT COUNT(*) FROM dishes
                         WHERE LOWER(ingredients) LIKE '%масл%'
                            OR name LIKE '%тунец%'
                            OR name LIKE '%wok%'
                            OR name LIKE '%киноа%'
                            OR name LIKE '%авокадо%'""")
            if c.fetchone()[0] > 0:
                need_rebuild = True
    except:
        need_rebuild = True

    if need_rebuild:
        c.execute("DROP TABLE IF EXISTS dishes")
        c.execute("""CREATE TABLE dishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_type TEXT, name TEXT,
            base_calories REAL, base_protein REAL, base_fat REAL,
            base_carbs REAL, base_weight REAL, ingredients TEXT
        )""")
        c.executemany("""INSERT INTO dishes
            (meal_type, name, base_calories, base_protein, base_fat, base_carbs, base_weight, ingredients)
            VALUES (?,?,?,?,?,?,?,?)""", DISHES_DATA)

    conn.commit()
    conn.close()


def get_dishes(meal_type):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("SELECT * FROM dishes WHERE meal_type=?", (meal_type,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_dish_by_name(name):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("SELECT * FROM dishes WHERE name=?", (name,))
    row = c.fetchone()
    conn.close()
    return row


# ===== ДНЕВНИК =====

def add_food_log(uid, meal_type, food_name, grams, cal, prot, fat, carb):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""INSERT INTO food_log
        (user_id, date, meal_type, food_name, grams, calories, protein, fat, carbs)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (uid, date.today().isoformat(), meal_type, food_name, grams, cal, prot, fat, carb))
    conn.commit()
    conn.close()


def get_food_today(uid):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""SELECT meal_type, food_name, grams, calories, protein, fat, carbs
                 FROM food_log WHERE user_id=? AND date=? ORDER BY id""",
        (uid, date.today().isoformat()))
    rows = c.fetchall()
    conn.close()
    return rows


def get_food_totals_today(uid):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0),
                        COALESCE(SUM(fat),0), COALESCE(SUM(carbs),0)
                 FROM food_log WHERE user_id=? AND date=?""",
        (uid, date.today().isoformat()))
    row = c.fetchone()
    conn.close()
    return {"calories": row[0], "protein": row[1], "fat": row[2], "carbs": row[3]}


def clear_food_today(uid):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("DELETE FROM food_log WHERE user_id=? AND date=?",
              (uid, date.today().isoformat()))
    conn.commit()
    conn.close()


def delete_last_food(uid):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""DELETE FROM food_log WHERE id = (
        SELECT id FROM food_log WHERE user_id=? AND date=?
        ORDER BY id DESC LIMIT 1)""",
        (uid, date.today().isoformat()))
    conn.commit()
    conn.close()
