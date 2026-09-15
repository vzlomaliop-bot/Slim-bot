from aiogram import Router, F
from aiogram.types import Message

from database import get_user, get_dishes, get_dish_by_name
from keyboards import main_menu, meals_menu_kb, dishes_kb
from meals_data import format_scaled_dish

router = Router()


@router.message(F.text == "🍽 Меню")
async def meals_menu(msg: Message):
    await msg.answer("Выбери приём пищи:", reply_markup=meals_menu_kb())


@router.message(F.text == "🍳 Завтрак")
async def breakfast(msg: Message):
    dishes = get_dishes("breakfast")
    await msg.answer("Варианты завтрака:", reply_markup=dishes_kb(dishes))


@router.message(F.text == "🍲 Обед")
async def lunch(msg: Message):
    dishes = get_dishes("lunch")
    await msg.answer("Варианты обеда:", reply_markup=dishes_kb(dishes))


@router.message(F.text == "🍽 Ужин")
async def dinner(msg: Message):
    dishes = get_dishes("dinner")
    await msg.answer("Варианты ужина:", reply_markup=dishes_kb(dishes))


@router.message(F.text.regexp(r"^[А-ЯЁа-яё].+$"))
async def maybe_dish(msg: Message):
    """Ловит нажатия на кнопки блюд (название без служебных символов)."""
    user = get_user(msg.from_user.id)
    if not user:
        return
    dish = get_dish_by_name(msg.text)
    if not dish:
        return
    text, _ = format_scaled_dish(dish, user["daily_calories"], dish[1])
    await msg.answer(text, parse_mode="Markdown", reply_markup=main_menu())
