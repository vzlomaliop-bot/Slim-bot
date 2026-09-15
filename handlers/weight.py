from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import get_user, add_weight, add_measurement
from keyboards import main_menu, weigh_type_kb

router = Router()


class WeightStates(StatesGroup):
    choosing_weigh_type = State()
    entering_weight = State()
    entering_measurements = State()


@router.message(F.text == "⚖️ Записать вес")
async def log_weight(msg: Message, state: FSMContext):
    await msg.answer(
        "⚖️ **Какой вес записываем?**\n\n"
        "🌅 **Натощак** — утром, после туалета, до еды (главный показатель)\n"
        "🌙 **Перед сном** — вечером, для справки",
        reply_markup=weigh_type_kb(),
        parse_mode="Markdown",
    )
    await state.set_state(WeightStates.choosing_weigh_type)


@router.message(WeightStates.choosing_weigh_type, F.text.in_(["🌅 Натощак (утро)", "🌙 Перед сном"]))
async def choose_weigh_type(msg: Message, state: FSMContext):
    wt = "fasted" if "Натощак" in msg.text else "fed"
    await state.update_data(weigh_type=wt)
    label = "натощак" if wt == "fasted" else "перед сном"
    await msg.answer(
        f"Введи вес ({label}) в кг — например `74.8`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(WeightStates.entering_weight)


@router.message(WeightStates.entering_weight)
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


@router.message(F.text == "📏 Замеры")
async def measure_menu(msg: Message, state: FSMContext):
    await msg.answer(
        "📏 Введи обхваты через пробел (в см):\n\n"
        "**шея грудь талия бёдра рука**\n\n"
        "Например: `38 100 92 98 32`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(WeightStates.entering_measurements)


@router.message(WeightStates.entering_measurements)
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
