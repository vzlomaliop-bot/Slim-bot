import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from database import (
    init_db, init_dishes, get_user,
)
from keyboards import main_menu
from scheduler import setup_scheduler
from handlers import (
    onboarding, water, weight, progress, meals, diary, workouts,
)

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()


# Подключаем все роутеры
dp.include_router(onboarding.router)
dp.include_router(water.router)
dp.include_router(weight.router)
dp.include_router(meals.router)
dp.include_router(diary.router)
dp.include_router(workouts.router)
dp.include_router(progress.router)


# ===== ОБЩИЕ КОМАНДЫ =====

@dp.message(F.text == "⬅️ В меню")
async def back_main(msg: Message):
    await msg.answer("Главное меню:", reply_markup=main_menu())


@dp.message(F.text == "👤 Профиль")
async def profile(msg: Message):
    user = get_user(msg.from_user.id)
    if not user:
        await msg.answer("Сначала /start", reply_markup=main_menu())
        return
    await msg.answer(
        f"👤 **Профиль**\n\n"
        f"Пол: {'М' if user['gender'] == 'm' else 'Ж'}\n"
        f"Возраст: {user['age']}\n"
        f"Рост: {user['height']} см\n"
        f"Текущий вес: {user['current_weight']} кг\n"
        f"Цель: {user['goal_weight']} кг\n"
        f"Норма: {user['daily_calories']} ккал/день\n"
        f"Вода: {user['daily_water']} мл/день",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


@dp.message(Command("help"))
async def help_cmd(msg: Message):
    await msg.answer(
        "**Как пользоваться:**\n\n"
        "💧 **Выпить воды** — отмечай, сколько выпил\n"
        "🍽 **Меню** — варианты завтрака/обеда/ужина под твою норму\n"
        "📝 **Дневник еды** — считай калории за день\n"
        "🔥 **Тренировка** — жиросжигающие комплексы\n"
        "⚖️ **Записать вес** — натощак утром + перед сном\n"
        "📏 **Замеры** — раз в неделю\n"
        "📊 **Прогресс** — динамика и прогноз\n"
        "📈 **График** — визуализация веса\n\n"
        "Команды: /start, /help",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


async def main():
    init_db()
    init_dishes()

    # Планировщик напоминаний
    try:
        setup_scheduler(bot)
        logging.info("Scheduler started")
    except Exception as e:
        logging.error(f"Scheduler error: {e}")

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
