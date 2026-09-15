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


def update_user(uid, field, value):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, uid))
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


def get_weights(uid, weigh_type="fasted", limit=30):
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


def get_days_active(uid):
    conn = sqlite3.connect("slim.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT date) FROM water WHERE user_id=?", (uid,))
    wd = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT date) FROM weights WHERE user_id=?", (uid,))
    wgd = c.fetchone()[0]
    conn.close()
    return wd, wgd
