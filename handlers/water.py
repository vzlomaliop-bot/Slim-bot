from aiogram import Router, F
from aiogram.types import Message

from database import get_user, get_water_today, add_water
from keyboards import main_menu, water_kb

router = Router()


def _progress_bar(total, goal):
    pct = min(100, int(total / goal * 100))
    bar = "▰" * (pct // 10) + "▱" * (10 - pct // 10)
    return bar, pct


@router.message(F.text == "💧 Выпить воды")
async def water_menu(msg: Message):
    user = get_user(msg.from_user.id)
    total = get_water_today(msg.from_user.id)
    goal = user["daily_water"] if user else 2500
    bar, pct = _progress_bar(total, goal)
    await msg.answer(
        f"💧 **Вода**\n\n{bar} {pct}%\n{total} мл из {goal} мл\n\nСколько выпил?",
        reply_markup=water_kb(),
        parse_mode="Markdown",
    )


@router.message(F.text.in_(["+250 мл", "+500 мл", "+750 мл", "+1000 мл"]))
async def add_water_cb(msg: Message):
    ml = int(msg.text.replace("+", "").replace(" мл", "").strip())
    add_water(msg.from_user.id, ml)
    user = get_user(msg.from_user.id)
    total = get_water_today(msg.from_user.id)
    goal = user["daily_water"] if user else 2500
    bar, pct = _progress_bar(total, goal)
    suffix = " 🎉 Цель достигнута!" if total >= goal else ""
    await msg.answer(
        f"✅ +{ml} мл\n\n{bar} {pct}%\n{total} мл из {goal} мл{suffix}",
        reply_markup=water_kb(),
    )
