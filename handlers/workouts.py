from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import random

from keyboards import main_menu
from workouts_data import WORKOUTS, format_workout

router = Router()


@router.message(F.text == "🔥 Тренировка")
async def workout_menu(msg: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Случайная тренировка", callback_data="wo_random")],
        [InlineKeyboardButton(text="🏠 Дома без инвентаря", callback_data="wo_0")],
        [InlineKeyboardButton(text="💥 HIIT на улице", callback_data="wo_1")],
        [InlineKeyboardButton(text="🏋️ Силовая в зале", callback_data="wo_2")],
        [InlineKeyboardButton(text="🏃 Кардио + пресс", callback_data="wo_3")],
        [InlineKeyboardButton(text="🏠 Дома с гантелями", callback_data="wo_4")],
    ])
    await msg.answer(
        "🔥 **Жиросжигающая тренировка**\n\n"
        "Выбери формат или возьми случайную:",
        reply_markup=kb,
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("wo_"))
async def workout_show(call: CallbackQuery):
    key = call.data.split("_")[1]
    if key == "random":
        w = random.choice(WORKOUTS)
    else:
        try:
            idx = int(key)
            w = WORKOUTS[idx % len(WORKOUTS)]
        except:
            w = random.choice(WORKOUTS)

    text = format_workout(w)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Другая", callback_data="wo_random")],
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
