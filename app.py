import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import (
    init_db, get_user, create_user,
    add_water, get_water_today, add_weight, get_weights, get_last_weight,
    add_measurement, get_days_active,
)

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()


class Onboard(StatesGroup):
    gender = State()
    age = State()
    height = State()
    weight = State()
    goal = State()
    activity = State()


class Actions(StatesGroup):
    choosing_weigh_type = State()
    entering_weight = State()
    entering_measurements = State()


def calc_calories(gender, age, height, weight, activity):
    if gender == "m":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    k = {"low": 1.2, "mid": 1.375, "high": 1.55}.get(activity, 1.375)
    return int(bmr * k - 500)


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💧 Выпить воды")],
            [KeyboardButton(text="⚖️ Записать вес")],
            [KeyboardButton(text="📏 Замеры")],
            [KeyboardButton(text="📊 Прогресс")],
            [KeyboardButton(text="👤 Профиль")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def water_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="+250 мл"), KeyboardButton(text="+500 мл")],
            [KeyboardButton(text="+750 мл"), KeyboardButton(text="+1000 мл")],
            [KeyboardButton(text="⬅️ В меню")],
        ],
        resize_keyboard=True,
    )


def weigh_type_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌅 Натощак (утро)")],
            [KeyboardButton(text="🌙 Перед сном")],
            [KeyboardButton(text="⬅️ В меню")],
        ],
        resize_keyboard=True,
    )


def onboard_gender_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Мужской"), KeyboardButton(text="👩 Женский")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def onboard_activity_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🪑 Малоподвижный")],
            [KeyboardButton(text="🚶 Средний (3-4 трен/нед)")],
            [KeyboardButton(text="🏃 Высокий (5+ трен/нед)")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@dp.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    await state.clear()
    user = get_user(msg.from_user.id)
    if user:
        await msg.answer(
            f"Привет, {msg.from_user.first_name}! 👋\n\n"
            f"🎯 Цель: {user['start_weight']} → {user['goal_weight']} кг\n"
            f"🍽 Норма: {user['daily_calories']} ккал/день\n"
            f"💧 Вода: {user['daily_water']} мл/день\n\n"
            f"Что делаем?",
            reply_markup=main_menu(),
        )
    else:
        await msg.answer(
            "Привет! 👋 Я помогу тебе сбросить вес без нервов.\n\n"
            "Ответь на 6 вопросов — я рассчитаю твою норму.\n\n"
            "**1. Твой пол?**",
            reply_markup=onboard_gender_kb(),
            parse_mode="Markdown",
        )
        await state.set_state(Onboard.gender)


@dp.message(Onboard.gender, F.text.in_(["👨 Мужской", "👩 Женский"]))
async def ob_gender(msg: Message, state: FSMContext):
    gender = "m" if "Мужской" in msg.text else "f"
    await state.update_data(gender=gender)
    await msg.answer(
        "**2. Сколько тебе лет?**\nНапример: `18`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(Onboard.age)


@dp.message(Onboard.age)
async def ob_age(msg: Message, state: FSMContext):
    try:
        age = int(msg.text.strip())
        assert 10 <= age <= 100
    except:
        await msg.answer("Введи число от 10 до 100.")
        return
    await state.update_data(age=age)
    await msg.answer("**3. Твой рост в см?**\nНапример: `173`", parse_mode="Markdown")
    await state.set_state(Onboard.height)


@dp.message(Onboard.height)
async def ob_height(msg: Message, state: FSMContext):
    try:
        h = int(msg.text.strip())
        assert 100 <= h <= 250
    except:
        await msg.answer("Введи рост в см (100-250).")
        return
    await state.update_data(height=h)
    await msg.answer("**4. Текущий вес в кг?**\nНапример: `75.2`", parse_mode="Markdown")
    await state.set_state(Onboard.weight)


@dp.message(Onboard.weight)
async def ob_weight(msg: Message, state: FSMContext):
    try:
        w = float(msg.text.replace(",", ".").strip())
        assert 30 <= w <= 300
    except:
        await msg.answer("Введи вес в кг (например 75.2).")
        return
    await state.update_data(start_weight=w)
    await msg.answer("**5. Целевой вес в кг?**\nНапример: `65`", parse_mode="Markdown")
    await state.set_state(Onboard.goal)


@dp.message(Onboard.goal)
async def ob_goal(msg: Message, state: FSMContext):
    try:
        g = float(msg.text.replace(",", ".").strip())
        data = await state.get_data()
        assert 30 <= g < data["start_weight"]
    except:
        await msg.answer("Цель должна быть меньше текущего веса.")
        return
    await state.update_data(goal_weight=g)
    await msg.answer(
        "**6. Уровень активности?**",
        reply_markup=onboard_activity_kb(),
        parse_mode="Markdown",
    )
    await state.set_state(Onboard.activity)


@dp.message(Onboard.activity, F.text.in_(["🪑 Малоподвижный", "🚶 Средний (3-4 трен/нед)", "🏃 Высокий (5+ трен/нед)"]))
async def ob_activity(msg: Message, state: FSMContext):
    if "Малоподвижный" in msg.text:
        act = "low"
    elif "Средний" in msg.text:
        act = "mid"
    else:
        act = "high"
    data = await state.get_data()
    data["activity"] = act
    data["username"] = msg.from_user.username
    data["daily_calories"] = calc_calories(
        data["gender"], data["age"], data["height"],
        data["start_weight"], act,
    )
    create_user(msg.from_user.id, data)
    await state.clear()
    await msg.answer(
        f"✅ Готово!\n\n"
        f"🎯 Цель: {data['start_weight']} → {data['goal_weight']} кг\n"
        f"🍽 Норма: ~{data['daily_calories']} ккал/день\n"
        f"💧 Вода: 2500 мл/день\n\n"
        f"Погнали!",
        reply_markup=main_menu(),
    )


@dp.message(F.text == "⬅️ В меню")
async def back_main(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Главное меню:", reply_markup=main_menu())


@dp.message(F.text == "💧 Выпить воды")
async def water_menu(msg: Message):
    user = get_user(msg.from_user.id)
    total = get_water_today(msg.from_user.id)
    goal = user["daily_water"] if user else 2500
    pct = min(100, int(total / goal * 100))
    bar = "▰" * (pct // 10) + "▱" * (10 - pct // 10)
    await msg.answer(
        f"💧 **Вода**\n\n{bar} {pct}%\n{total} мл из {goal} мл\n\nСколько выпил?",
        reply_markup=water_kb(),
        parse_mode="Markdown",
    )


@dp.message(F.text.in_(["+250 мл", "+500 мл", "+750 мл", "+1000 мл"]))
async def add_water_cb(msg: Message):
    ml = int(msg.text.replace("+", "").replace(" мл", "").strip())
    add_water(msg.from_user.id, ml)
    user = get_user(msg.from_user.id)
    total = get_water_today(msg.from_user.id)
    goal = user["daily_water"] if user else 2500
    pct = min(100, int(total / goal * 100))
    bar = "▰" * (pct // 10) + "▱" * (10 - pct // 10)
    suffix = " 🎉 Цель достигнута!" if total >= goal else ""
    await msg.answer(
        f"✅ +{ml} мл\n\n{bar} {pct}%\n{total} мл из {goal} мл{suffix}",
        reply_markup=water_kb(),
    )


@dp.message(F.text == "⚖️ Записать вес")
async def log_weight(msg: Message, state: FSMContext):
    await msg.answer(
        "⚖️ **Какой вес записываем?**\n\n"
        "🌅 **Натощак** — утром, после туалета, до еды (главный показатель)\n"
        "🌙 **Перед сном** — вечером, для справки",
        reply_markup=weigh_type_kb(),
        parse_mode="Markdown",
    )
    await state.set_state(Actions.choosing_weigh_type)


@dp.message(Actions.choosing_weigh_type, F.text.in_(["🌅 Натощак (утро)", "🌙 Перед сном"]))
async def choose_weigh_type(msg: Message, state: FSMContext):
    wt = "fasted" if "Натощак" in msg.text else "fed"
    await state.update_data(weigh_type=wt)
    label = "натощак" if wt == "fasted" else "перед сном"
    await msg.answer(
        f"Введи вес ({label}) в кг — например `74.8`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(Actions.entering_weight)


@dp.message(Actions.entering_weight)
async def save_weight(msg: Message, state: FSMContext):
    try:
        w = float(msg.text.replace(",", ".").strip())
        assert 30 <= w <= 300
    except:
        await msg.answer("Введи число (например 74.8).")
        return
    data = await state.get_data()
    wt = data.get("weigh_type", "fasted")
    add_weight(msg.from_user.id, w, wt)
    user = get_user(msg.from_user.id)
    left = round(w - user["goal_weight"], 1)
    label = "натощак 🌅" if wt == "fasted" else "перед сном 🌙"
    await state.clear()
    await msg.answer(
        f"✅ Записал ({label}): {w} кг\n\nОсталось до цели: **{left} кг**",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


@dp.message(F.text == "📏 Замеры")
async def measure_menu(msg: Message, state: FSMContext):
    await msg.answer(
        "📏 Введи обхваты через пробел (в см):\n\n"
        "**шея грудь талия бёдра рука**\n\n"
        "Например: `38 100 92 98 32`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(Actions.entering_measurements)


@dp.message(Actions.entering_measurements)
async def save_measure(msg: Message, state: FSMContext):
    try:
        parts = msg.text.replace(",", ".").split()
        neck, chest, waist, hips, arm = [float(x) for x in parts[:5]]
    except:
        await msg.answer("Нужно 5 чисел через пробел: шея грудь талия бёдра рука")
        return
    add_measurement(msg.from_user.id, neck, chest, waist, hips, arm)
    await state.clear()
    await msg.answer(
        f"✅ Замеры сохранены:\n"
        f"Шея: {neck}\nГрудь: {chest}\nТалия: {waist}\nБёдра: {hips}\nРука: {arm}",
        reply_markup=main_menu(),
    )


@dp.message(F.text == "📊 Прогресс")
async def progress(msg: Message):
    user = get_user(msg.from_user.id)
    fasted = get_weights(msg.from_user.id, "fasted", 14)
    last_fed = get_last_weight(msg.from_user.id, "fed")
    wd, wgd = get_days_active(msg.from_user.id)

    lines = ["📊 **Твой прогресс**\n"]

    if user:
        lost = round(user["start_weight"] - user["current_weight"], 1)
        left = round(user["current_weight"] - user["goal_weight"], 1)
        lines.append(f"🎯 {user['start_weight']} → {user['goal_weight']} кг")
        lines.append(f"📉 Сброшено: **{lost} кг**")
        lines.append(f"⏳ Осталось: **{left} кг**")
        lines.append("")

    if fasted:
        lines.append("🌅 **Натощак (последние):**")
        for d, w in fasted[-7:]:
            lines.append(f"• {d}: {w} кг")
        lines.append("")
    else:
        lines.append("🌅 Натощак: пока пусто\n")

    if last_fed:
        lines.append(f"🌙 Перед сном: {last_fed[0]}: {last_fed[1]} кг")
        lines.append("")

    lines.append(f"💧 Дней с водой: {wd}")
    lines.append(f"⚖️ Дней с весом: {wgd}")

    await msg.answer("\n".join(lines), reply_markup=main_menu(), parse_mode="Markdown")


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
        "⚖️ **Записать вес** — натощак утром + перед сном вечером\n"
        "📏 **Замеры** — раз в неделю\n"
        "📊 **Прогресс** — динамика\n\n"
        "Команды: /start, /help",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
