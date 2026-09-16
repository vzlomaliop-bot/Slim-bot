import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import get_all_users, get_water_today, get_last_weight


scheduler = AsyncIOScheduler()
_bot = None


async def _check_reminders():
    """Запускается каждый час в :00. Проверяет личные настройки каждого юзера."""
    if _bot is None:
        return
    now_hour = datetime.now().hour
    today = datetime.now().date().isoformat()

    for u in get_all_users():
        uid = u["user_id"]

        # Вода
        if u["remind_water"]:
            hours = []
            for h in (u["water_hours"] or "").split(","):
                h = h.strip()
                if h.isdigit() and 0 <= int(h) <= 23:
                    hours.append(int(h))
            if now_hour in hours:
                try:
                    total = get_water_today(uid)
                    await _bot.send_message(
                        uid,
                        f"💧 Пора попить воды!\n\nСегодня: {total} мл. Открой меню и нажми «💧 Выпить воды»."
                    )
                except Exception as e:
                    logging.warning(f"water reminder to {uid}: {e}")

        # Взвешивание
        if u["remind_weigh"] and now_hour == u["weigh_hour"]:
            # Проверяем, взвесился ли уже натощак сегодня
            last = get_last_weight(uid, "fasted")
            if not last or last[0] != today:
                try:
                    await _bot.send_message(
                        uid,
                        "⚖️ Доброе утро! Не забудь взвеситься натощак и записать вес."
                    )
                except Exception as e:
                    logging.warning(f"weigh reminder to {uid}: {e}")


async def _weekly_measure():
    if _bot is None:
        return
    for u in get_all_users():
        try:
            await _bot.send_message(
                u["user_id"],
                "📏 Воскресенье — время замеров! Запиши обхваты через 📏 Замеры."
            )
        except Exception:
            pass


def setup_scheduler(bot):
    global _bot
    _bot = bot

    # Каждый час в :00 — проверка личных настроек напоминаний
    scheduler.add_job(_check_reminders, "cron", minute=0, id="hourly_reminders")
    # Воскресенье 11:00 — напоминание о замерах
    scheduler.add_job(_weekly_measure, "cron", day_of_week="sun", hour=11, minute=0, id="weekly_measure")

    scheduler.start()
