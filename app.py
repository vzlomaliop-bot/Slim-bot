import asyncio
import logging
from datetime import date

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import (
    init_db, get_user, create_user, update_user,
    add_water, get_water_today, add_weight, get_weights,
    add_measurement, get_measurements, get_days_active,
)

logging.basicConfig(level=logging.INFO)
import os
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
    entering_weight = State()
    entering_measurements = State()


# ---------- Расчёт калорий ----------
def calc_calories(gender, age, height, weight, activity):
    # Mifflin-St Jeor
    if gender == "m":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    k = {"low": 1.2, "mid": 1.375, "high": 1.55}.get(activity, 1.375)
    tdee = bmr * k
    return int(tdee - 500)  # дефицит 500 ккал = ~0.5 кг/нед


# ---------- Клавиатуры ----------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💧 Выпить воды", callback_data="water_menu")],
        [InlineKeyboardButton(text="⚖️ Записать вес", callback_data="log_weight")],
        [InlineKeyboardButton(text="📏 Замеры", callback_data="measure_menu")],
        [InlineKeyboardButton(text="📊 Прогресс", callback_data="progress")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ])


def water_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="+250 мл", callback_data="w_250"),
         InlineKeyboardButton(text="+500 мл", callback_data="w_500")],
        [InlineKeyboardButton(text="+750 мл", callback_data="w_750"),
         InlineKeyboardButton(text="+1000 мл", callback_data="w_1000")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")],
    ])


def onboard_gender_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Мужской", callback_data="g_m")],
        [InlineKeyboardButton(text="👩 Женский", callback_data="g_f")],
    ])


def onboard_activity_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪑 Малоподвижный", callback_data="a_low")],
        [InlineKeyboardButton(text="🚶 Средний (3-4 трен/нед)", callback_data="a_mid")],
        [InlineKeyboardButton(text="🏃 Высокий (5+ трен/нед)", callback_data="a_high")],
    ])


def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_main")]
    ])


# ---------- /start ----------
@dp.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    await state.clear()
    user = get_user(msg.from_user.id)
    if user:
        await msg.answer(
            f"Привет, {msg.from_user.first_name}! 👋\n\n"
            f"Твоя цель: {user['start_weight']} → {user['goal_weight']} кг\n"
            f"Норма: {user['daily_calories']} ккал/день, вода {user['daily_water']} мл\n\n"
            f"Что делаем?",
            reply_markup=main_menu(),
        )
    else:
        await msg.answer(
            "Привет! 👋 Я помогу тебе сбросить вес без нервов — с водой, замерами и трекингом прогресса.\n\n"
            "Ответь на несколько вопросов, чтобы я рассчитал твою норму.\n\n"
            "**1. Твой пол?**",
            reply_markup=onboard_gender_kb(),
            parse_mode="Markdown",
        )
        await state.set_state(Onboard.gender)


@dp.callback_query(Onboard.gender, F.data.startswith("g_"))
async def ob_gender(call: CallbackQuery, state: FSMContext):
    gender = call.data.split("_")[1]
    await state.update_data(gender=gender)
    await call.message.edit_text("**2. Сколько тебе лет?** (число)\nНапример: `28`", parse_mode="Markdown")
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
    await msg.answer("**3. Твой рост в см?**\nНапример: `178`", parse_mode="Markdown")
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
    await msg.answer("**4. Текущий вес в кг?**\nНапример: `92.5`", parse_mode="Markdown")
    await state.set_state(Onboard.weight)


@dp.message(Onboard.weight)
async def ob_weight(msg: Message, state: FSMContext):
    try:
        w = float(msg.text.replace(",", ".").strip())
        assert 30 <= w <= 300
    except:
        await msg.answer("Введи вес в кг (например 92.5).")
        return
    await state.update_data(start_weight=w)
    await msg.answer("**5. Целевой вес в кг?**\nНапример: `80`", parse_mode="Markdown")
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
    await msg.answer("**6. Уровень активности?**", reply_markup=onboard_activity_kb(), parse_mode="Markdown")
    await state.set_state(Onboard.activity)


@dp.callback_query(Onboard.activity, F.data.startswith("a_"))
async def ob_activity(call: CallbackQuery, state: FSMContext):
    act = call.data.split("_")[1]
    data = await state.get_data()
    data["activity"] = act
    data["username"] = call.from_user.username
    data["daily_calories"] = calc_calories(
        data["gender"], data["age"], data["height"],
        data["start_weight"], act,
    )
    create_user(call.from_user.id, data)
    await state.clear()
    await call.message.edit_text(
        f"✅ Готово!\n\n"
        f"🎯 Цель: {data['start_weight']} → {data['goal_weight']} кг\n"
        f"🍽 Норма: ~{data['daily_calories']} ккал/день\n"
        f"💧 Вода: 2500 мл/день\n\n"
        f"Погнали!",
        reply_markup=main_menu(),
    )


# ---------- Главное меню ----------
@dp.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Главное меню:", reply_markup=main_menu())


# ---------- Вода ----------
@dp.callback_query(F.data == "water_menu")
async def water_menu(call: CallbackQuery):
    user = get_user(call.from_user.id)
    total = get_water_today(call.from_user.id)
    goal = user["daily_water"] if user else 2500
    pct = min(100, int(total / goal * 100))
    bar = "▰" * (pct // 10) + "▱" * (10 - pct // 10)
    await call.message.edit_text(
        f"💧 **Вода**\n\n{bar} {pct}%\n{total} мл из {goal} мл\n\nСколько выпил?",
        reply_markup=water_kb(),
        parse_mode="Markdown",
    )


@dp.callback_query(F.data.startswith("w_"))
async def add_water_cb(call: CallbackQuery):
    ml = int(call.data.split("_")[1])
    add_water(call.from_user.id, ml)
    user = get_user(call.from_user.id)
    total = get_water_today(call.from_user.id)
    goal = user["daily_water"] if user else 2500
    pct = min(100, int(total / goal * 100))
    bar = "▰" * (pct // 10) + "▱" * (10 - pct // 10)
    suffix = " 🎉 Цель достигнута!" if total >= goal else ""
    await call.message.edit_text(
        f"✅ +{ml} мл\n\n{bar} {pct}%\n{total} мл из {goal} мл{suffix}",
        reply_markup=water_kb(),
    )


# ---------- Вес ----------
@dp.callback_query(F.data == "log_weight")
async def log_weight(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("⚖️ Введи свой вес в кг (например `91.8`):", parse_mode="Markdown")
    await state.set_state(Actions.entering_weight)


@dp.message(Actions.entering_weight)
async def save_weight(msg: Message, state: FSMContext):
    try:
        w = float(msg.text.replace(",", ".").strip())
        assert 30 <= w <= 300
    except:
        await msg.answer("Введи число (например 91.8).")
        return
    add_weight(msg.from_user.id, w)
    user = get_user(msg.from_user.id)
    left = round(w - user["goal_weight"], 1)
    await state.clear()
    await msg.answer(
        f"✅ Записал: {w} кг\n\nОсталось до цели: **{left} кг**",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


# ---------- Замеры ----------
@dp.callback_query(F.data == "measure_menu")
async def measure_menu(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "📏 Введи обхваты через пробел (в см):\n\n"
        "**шея грудь талия бёдра рука**\n\n"
        "Например: `38 100 92 98 32`",
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


# ---------- Прогресс ----------
@dp.callback_query(F.data == "progress")
async def progress(call: CallbackQuery):
    user = get_user(call.from_user.id)
    weights = get_weights(call.from_user.id, 10)
    wd, wgd = get_days_active(call.from_user.id)

    lines = ["📊 **Твой прогресс**\n"]
    if user:
        lost = round(user["start_weight"] - user["current_weight"], 1)
        left = round(user["current_weight"] - user["goal_weight"], 1)
        lines.append(f"🎯 {user['start_weight']} → {user['goal_weight']} кг")
        lines.append(f"📉 Сброшено: **{lost} кг**")
        lines.append(f"⏳ Осталось: **{left} кг**\n")

    lines.append(f"💧 Дней с водой: {wd}")
    lines.append(f"⚖️ Дней с весом: {wgd}\n")

    if weights:
        lines.append("**Последние замеры веса:**")
        for d, w in weights[-7:]:
            lines.append(f"• {d}: {w} кг")

    await call.message.edit_text("\n".join(lines), reply_markup=back_kb(), parse_mode="Markdown")


# ---------- Профиль ----------
@dp.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    user = get_user(call.from_user.id)
    if not user:
        await call.message.edit_text("Сначала /start", reply_markup=back_kb())
        return
    await call.message.edit_text(
        f"👤 **Профиль**\n\n"
        f"Пол: {'М' if user['gender'] == 'm' else 'Ж'}\n"
        f"Возраст: {user['age']}\n"
        f"Рост: {user['height']} см\n"
        f"Текущий вес: {user['current_weight']} кг\n"
        f"Цель: {user['goal_weight']} кг\n"
        f"Норма: {user['daily_calories']} ккал/день\n"
        f"Вода: {user['daily_water']} мл/день",
        reply_markup=back_kb(),
        parse_mode="Markdown",
    )


@dp.message(Command("help"))
async def help_cmd(msg: Message):
    await msg.answer(
        "**Как пользоваться ботом:**\n\n"
        "💧 **Вода** — жми кнопку и отмечай, сколько выпил\n"
        "⚖️ **Вес** — записывай каждое утро\n"
        "📏 **Замеры** — раз в неделю (шея, грудь, талия, бёдра, рука)\n"
        "📊 **Прогресс** — смотри, как уходит вес\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "/progress — прогресс\n"
        "/help — эта справка",
        parse_mode="Markdown",
    )


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
