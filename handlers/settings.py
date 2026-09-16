from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import get_user, update_user
from keyboards import main_menu, settings_kb, settings_back_kb

router = Router()


class SettingsStates(StatesGroup):
    waiting_water_hours = State()
    waiting_weigh_hour = State()


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(msg: Message):
    user = get_user(msg.from_user.id)
    if not user:
        await msg.answer("Сначала /start", reply_markup=main_menu())
        return

    water_hours = user.get("water_hours") or "10,13,16,19,22"
    weigh_hour = user.get("weigh_hour") or 8
    remind_water = "вкл ✅" if user.get("remind_water") else "выкл ❌"
    remind_weigh = "вкл ✅" if user.get("remind_weigh") else "выкл ❌"

    text = (
        f"⚙️ **Настройки напоминаний**\n\n"
        f"💧 Вода: каждый час из списка [{water_hours}]\n"
        f"⚖️ Взвешивание: {weigh_hour}:00\n\n"
        f"Статус:\n"
        f"• Вода: {remind_water}\n"
        f"• Вес: {remind_weigh}\n\n"
        f"Выбери, что изменить:"
    )
    await msg.answer(text, reply_markup=settings_kb(), parse_mode="Markdown")


@router.message(F.text == "💧 Время воды")
async def set_water_hours(msg: Message, state: FSMContext):
    await msg.answer(
        "Введи **часы** для напоминаний о воде через запятую (от 0 до 23).\n\n"
        "Например: `9,12,15,18,21`\n\n"
        "Или нажми ⬅️ Назад для отмены.",
        reply_markup=settings_back_kb(),
        parse_mode="Markdown",
    )
    await state.set_state(SettingsStates.waiting_water_hours)


@router.message(SettingsStates.waiting_water_hours)
async def save_water_hours(msg: Message, state: FSMContext):
    if msg.text == "⬅️ Назад":
        await state.clear()
        await settings_menu(msg)
        return
    try:
        parts = [p.strip() for p in msg.text.split(",")]
        hours = []
        for p in parts:
            h = int(p)
            if 0 <= h <= 23:
                hours.append(h)
        assert 1 <= len(hours) <= 12
        hours_str = ",".join(str(h) for h in sorted(set(hours)))
    except:
        await msg.answer("Не понял. Введи часы через запятую, например: `9,12,15,18,21`",
                         parse_mode="Markdown")
        return
    update_user(msg.from_user.id, "water_hours", hours_str)
    await state.clear()
    await msg.answer(f"✅ Сохранил: вода в [{hours_str}]", reply_markup=settings_kb())


@router.message(F.text == "⚖️ Время веса")
async def set_weigh_hour(msg: Message, state: FSMContext):
    await msg.answer(
        "Введи **час** для напоминания о взвешивании (от 0 до 23).\n\n"
        "Например: `8` — напомнит в 8:00\n\n"
        "Или нажми ⬅️ Назад для отмены.",
        reply_markup=settings_back_kb(),
        parse_mode="Markdown",
    )
    await state.set_state(SettingsStates.waiting_weigh_hour)


@router.message(SettingsStates.waiting_weigh_hour)
async def save_weigh_hour(msg: Message, state: FSMContext):
    if msg.text == "⬅️ Назад":
        await state.clear()
        await settings_menu(msg)
        return
    try:
        h = int(msg.text.strip())
        assert 0 <= h <= 23
    except:
        await msg.answer("Введи число от 0 до 23.")
        return
    update_user(msg.from_user.id, "weigh_hour", str(h))
    await state.clear()
    await msg.answer(f"✅ Сохранил: взвешивание в {h}:00", reply_markup=settings_kb())


@router.message(F.text == "🔔 Вкл/выкл воду")
async def toggle_water(msg: Message):
    user = get_user(msg.from_user.id)
    new_val = 0 if user.get("remind_water") else 1
    update_user(msg.from_user.id, "remind_water", str(new_val))
    state = "включены ✅" if new_val else "выключены ❌"
    await msg.answer(f"Напоминания о воде {state}.", reply_markup=settings_kb())


@router.message(F.text == "🔔 Вкл/выкл вес")
async def toggle_weigh(msg: Message):
    user = get_user(msg.from_user.id)
    new_val = 0 if user.get("remind_weigh") else 1
    update_user(msg.from_user.id, "remind_weigh", str(new_val))
    state = "включены ✅" if new_val else "выключены ❌"
    await msg.answer(f"Напоминания о весе {state}.", reply_markup=settings_kb())
