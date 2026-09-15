from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import get_user, create_user
from keyboards import main_menu, onboard_gender_kb, onboard_activity_kb

router = Router()


class Onboard(StatesGroup):
    gender = State()
    age = State()
    height = State()
    weight = State()
    goal = State()
    activity = State()


def calc_calories(gender, age, height, weight, activity):
    if gender == "m":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    k = {"low": 1.2, "mid": 1.375, "high": 1.55}.get(activity, 1.375)
    return int(bmr * k - 500)


@router.message(Command("start"))
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


@router.message(Onboard.gender, F.text.in_(["👨 Мужской", "👩 Женский"]))
async def ob_gender(msg: Message, state: FSMContext):
    gender = "m" if "Мужской" in msg.text else "f"
    await state.update_data(gender=gender)
    await msg.answer(
        "**2. Сколько тебе лет?**\nНапример: `25`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(Onboard.age)


@router.message(Onboard.age)
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


@router.message(Onboard.height)
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


@router.message(Onboard.weight)
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


@router.message(Onboard.goal)
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


@router.message(Onboard.activity, F.text.in_(["🪑 Малоподвижный", "🚶 Средний (3-4 трен/нед)", "🏃 Высокий (5+ трен/нед)"]))
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
