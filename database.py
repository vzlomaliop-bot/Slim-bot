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

    c.execute("""CREATE TABLE IF NOT EXISTS water (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        ml INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        weight REAL,
        weigh_type TEXT DEFAULT 'fasted'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        neck REAL, chest REAL, waist REAL, hips REAL, arm REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS dishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_type TEXT,
        name TEXT,
        base_calories REAL,
        base_protein REAL,
        base_fat REAL,
        base_carbs REAL,
        base_weight REAL,
        ingredients TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS food_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        meal_type TEXT,
        food_name TEXT,
        grams REAL,
        calories REAL,
        protein REAL,
        fat REAL,
        carbs REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_foods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        per100_cal REAL,
        per100_prot REAL,
        per100_fat REAL,
        per100_carb REAL
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
            "goal_weight","activity","daily_calories","daily_water","created_at"]
    return dict(zip(keys, row))


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


def get_measurements(uid, limit=10):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""SELECT date, neck, chest, waist, hips, arm FROM measurements
                 WHERE user_id=? ORDER BY date DESC LIMIT ?""", (uid, limit))
    rows = c.fetchall()
    conn.close()
    return rows


# ===== БЛЮДА =====

def init_dishes():
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dishes")
    if c.fetchone()[0] == 0:
        dishes = [
            # ===== ЗАВТРАКИ =====
            ("breakfast", "Овсянка с ягодами", 320, 12, 8, 48, 300,
             "Овсянка 60г, Молоко 150мл, Ягоды 80г, Мёд 1ч.л."),
            ("breakfast", "Омлет с овощами", 280, 20, 18, 6, 250,
             "Яйца 3шт, Помидор 1шт, Перец 50г, Масло 1ч.л."),
            ("breakfast", "Творог с бананом", 300, 25, 6, 38, 280,
             "Творог 5% 180г, Банан 1шт, Корица"),
            ("breakfast", "Сырники с ягодами", 340, 22, 12, 38, 270,
             "Творог 5% 200г, Яйцо 1шт, Мука 30г, Ягоды 80г"),
            ("breakfast", "Греческий йогурт с гранолой", 290, 18, 9, 36, 250,
             "Йогурт греч. 200г, Гранола 40г, Ягоды 50г"),
            ("breakfast", "Яичница с беконом", 380, 24, 28, 4, 220,
             "Яйца 3шт, Бекон 40г, Масло 1ч.л."),
            ("breakfast", "Овсяноблин с творогом", 330, 25, 10, 34, 280,
             "Овсянка 40г, Яйца 2шт, Творог 5% 100г"),
            ("breakfast", "Тост с авокадо и яйцом", 350, 16, 20, 28, 240,
             "Хлеб цельнозерн. 60г, Авокадо 70г, Яйцо 1шт"),
            ("breakfast", "Каша рисовая на молоке", 310, 10, 7, 50, 320,
             "Рис 60г, Молоко 200мл, Мёд 1ч.л., Изюм 20г"),
            ("breakfast", "Бутерброд с лососем", 340, 22, 16, 26, 220,
             "Хлеб цельнозерн. 60г, Лосось 80г, Сыр творожный 30г"),
            ("breakfast", "Смузи-боул", 300, 12, 8, 44, 300,
             "Банан 1шт, Ягоды 100г, Йогурт 150г, Овсянка 30г"),
            ("breakfast", "Шакшука", 320, 18, 20, 16, 300,
             "Яйца 2шт, Томаты 200г, Перец 80г, Лук 50г, Масло 1ч.л."),
            # ===== ОБЕДЫ =====
            ("lunch", "Курица с гречкой и салатом", 480, 42, 12, 52, 400,
             "Куриное филе 150г, Гречка 80г (сухая), Овощи 150г, Масло 1ч.л."),
            ("lunch", "Рыба с рисом и овощами", 450, 38, 14, 48, 420,
             "Треска 180г, Рис 70г (сухой), Брокколи 150г, Масло 1ч.л."),
            ("lunch", "Индейка с булгуром", 470, 40, 13, 50, 410,
             "Индейка 160г, Булгур 70г, Овощи 150г, Оливк. масло 1ч.л."),
            ("lunch", "Говядина с картофелем", 520, 38, 18, 50, 450,
             "Говядина 160г, Картофель 200г, Овощи 100г"),
            ("lunch", "Паста с курицей", 500, 36, 14, 58, 400,
             "Паста 70г (сухая), Курица 130г, Томатный соус 100г"),
            ("lunch", "Плов с курицей", 510, 34, 16, 56, 420,
             "Рис 80г, Курица 130г, Морковь 80г, Лук 50г, Масло 1ч.л."),
            ("lunch", "Стейк с овощами гриль", 490, 42, 24, 24, 420,
             "Стейк 180г, Кабачок 150г, Перец 100г, Оливк. масло 1ч.л."),
            ("lunch", "Куриный суп с овощами", 380, 30, 10, 40, 500,
             "Курица 120г, Картофель 100г, Морковь 60г, Лук 40г"),
            ("lunch", "Борщ с говядиной", 420, 26, 14, 44, 500,
             "Говядина 130г, Свёкла 100г, Капуста 100г, Картофель 80г"),
            ("lunch", "Киноа с овощами и курицей", 460, 38, 12, 48, 420,
             "Киноа 70г, Курица 130г, Овощи 150г, Масло 1ч.л."),
            ("lunch", "Ролл с курицей (цельнозерн.)", 440, 32, 14, 46, 380,
             "Лаваш цельнозерн. 80г, Курица 130г, Овощи 100г, Соус 20г"),
            ("lunch", "Чечевичный суп", 400, 26, 8, 56, 500,
             "Чечевица 80г, Морковь 60г, Лук 40г, Масло 1ч.л."),
            ("lunch", "Тёплый салат с тунцом", 380, 36, 16, 20, 350,
             "Тунец 150г, Овощи 200г, Яйцо 1шт, Оливк. масло 1ч.л."),
            ("lunch", "Котлеты из индейки с пюре", 490, 36, 16, 50, 430,
             "Фарш индейки 160г, Картофель 180г, Молоко 50мл"),
            # ===== УЖИНЫ =====
            ("dinner", "Стейк лосося с овощами", 420, 34, 22, 18, 350,
             "Лосось 180г, Спаржа 100г, Кабачок 150г, Лимон"),
            ("dinner", "Куриное филе с тушёными овощами", 380, 40, 10, 28, 400,
             "Куриное филе 180г, Овощи 200г, Масло 1ч.л."),
            ("dinner", "Творожная запеканка", 350, 30, 12, 30, 320,
             "Творог 5% 200г, Яйцо 1шт, Овсянка 30г, Мёд 1ч.л."),
            ("dinner", "Индейка с брокколи", 360, 38, 11, 22, 380,
             "Индейка 180г, Брокколи 200г, Масло 1ч.л."),
            ("dinner", "Омлет с шпинатом", 320, 26, 20, 8, 300,
             "Яйца 3шт, Шпинат 100г, Сыр 20г"),
            ("dinner", "Запечённая рыба с овощами", 380, 36, 16, 22, 400,
             "Треска 200г, Кабачок 150г, Перец 100г, Масло 1ч.л."),
            ("dinner", "Креветки с овощами wok", 340, 32, 12, 24, 350,
             "Креветки 180г, Овощи 200г, Масло 1ч.л., Соевый соус"),
            ("dinner", "Куриная грудка с салатом", 350, 40, 10, 20, 400,
             "Курица 180г, Салат 150г, Огурец 80г, Оливк. масло 1ч.л."),
            ("dinner", "Тушёная говядина с овощами", 420, 36, 18, 26, 400,
             "Говядина 170г, Овощи 200г, Масло 1ч.л."),
            ("dinner", "Творог с огурцом и зеленью", 280, 30, 10, 14, 300,
             "Творог 5% 200г, Огурец 80г, Зелень, Оливк. масло 1ч.л."),
            ("dinner", "Котлеты из индейки на пару", 340, 36, 12, 20, 320,
             "Фарш индейки 180г, Лук 30г, Яйцо 1шт"),
            ("dinner", "Салат с креветками и авокадо", 360, 26, 22, 14, 350,
             "Креветки 150г, Авокадо 70г, Салат 100г, Оливк. масло 1ч.л."),
        ]
        c.executemany("""INSERT INTO dishes
            (meal_type, name, base_calories, base_protein, base_fat, base_carbs, base_weight, ingredients)
            VALUES (?,?,?,?,?,?,?,?)""", dishes)
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


# ===== ДНЕВНИК ЕДЫ =====

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
                 FROM food_log WHERE user_id=? AND date=?
                 ORDER BY id""", (uid, date.today().isoformat()))
    rows = c.fetchall()
    conn.close()
    return rows


def get_food_totals_today(uid):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""SELECT
        COALESCE(SUM(calories),0),
        COALESCE(SUM(protein),0),
        COALESCE(SUM(fat),0),
        COALESCE(SUM(carbs),0)
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
        ORDER BY id DESC LIMIT 1
    )""", (uid, date.today().isoformat()))
    conn.commit()
    conn.close()


# ===== ЛИЧНЫЕ ПРОДУКТЫ =====

def add_user_food(uid, name, cal, prot, fat, carb):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""INSERT INTO user_foods
        (user_id, name, per100_cal, per100_prot, per100_fat, per100_carb)
        VALUES (?,?,?,?,?,?)""", (uid, name, cal, prot, fat, carb))
    conn.commit()
    conn.close()


def get_user_foods(uid):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("""SELECT name, per100_cal, per100_prot, per100_fat, per100_carb
                 FROM user_foods WHERE user_id=? ORDER BY name""", (uid,))
    rows = c.fetchall()
    conn.close()
    return rows


def find_food(uid, query):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    q = f"%{query.lower()}%"
    c.execute("""SELECT name, per100_cal, per100_prot, per100_fat, per100_carb
                 FROM user_foods WHERE user_id=? AND LOWER(name) LIKE ?""", (uid, q))
    user_rows = c.fetchall()
    conn.close()
    return user_rows
