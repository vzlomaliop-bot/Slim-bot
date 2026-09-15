import sqlite3
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler


scheduler = AsyncIOScheduler()


def _get_all_users():
    conn = sqlite3.connect("/app/data/slim.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def setup_scheduler(bot):
    """Регистрирует фоновые напоминания."""

    async def remind_water():
        for uid in _get_all_users():
            try:
                await bot.send_message(
                    uid,
                    "💧 Напоминание: пора выпить стакан воды!",
                )
            except Exception:
                pass

    async def remind_weigh():
        for uid in _get_all_users():
            try:
                await bot.send_message(
                    uid,
                    "⚖️ Доброе утро! Не забудь взвеситься натощак и записать вес.",
                )
            except Exception:
                pass

    async def remind_measure():
        for uid in _get_all_users():
            try:
                await bot.send_message(
                    uid,
                    "📏 Воскресенье — время замеров! Запиши обхваты через 📏 Замеры.",
                )
            except Exception:
                pass

    # Пить воду — каждые 3 часа с 10 до 22
    scheduler.add_job(remind_water, "cron", hour="10,13,16,19,22", minute=0, id="water")
    # Взвешивание — каждое утро в 8:00
    scheduler.add_job(remind_weigh, "cron", hour=8, minute=0, id="weigh")
    # Замеры — воскресенье в 11:00
    scheduler.add_job(remind_measure, "cron", day_of_week="sun", hour=11, minute=0, id="measure")

    scheduler.start()
