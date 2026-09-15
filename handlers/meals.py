from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import (
    get_user, get_dishes, get_dish_by_name,
    add_food_log, get_food_totals_today,
)
from keyboards import (
    main_menu, meals_menu_kb, dishes_kb, dish_preview_kb, diary_menu_kb,
)
from meals_data import scale_dish

router = Router()


# Храним последнее выбранное блюдо для каждого пользователя (в памяти)
_last_dish = {}


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
async def dish_preview(msg: Message):
    """Когда пользователь нажал блюдо — показываем предпросмотр с кнопками."""
    user = get_user(msg.from_user.id)
    if not user:
        return
    dish = get_dish_by_name(msg.text)
    if not dish:
        return

    scaled = scale_dish(dish, user["daily_calories"], dish[1])
    _last_dish[msg.from_user.id] = scaled

    text = (
        f"🍽 **{scaled['name']}**\n\n"
        f"🎯 Под твою норму ({user['daily_calories']} ккал/день):\n\n"
        f"⚖️ Порция: **{scaled['weight']} г**\n"
        f"🔥 Калории: {scaled['calories']} ккал\n"
        f"🥩 Белки: {scaled['protein']} г\n"
        f"🥑 Жиры: {scaled['fat']} г\n"
        f"🍚 Углеводы: {scaled['carbs']} г\n\n"
        f"📝 Состав:\n{scaled['ingredients']}\n\n"
        f"_Коэффициент порции: ×{scaled['coefficient']}_"
    )
    await msg.answer(text, parse_mode="Markdown",
                     reply_markup=dish_preview_kb(dish[1]))


@router.callback_query(F.data.startswith("add_dish_"))
async def add_dish_to_diary(call: CallbackQuery):
    meal_type = call.data.replace("add_dish_", "")
    scaled = _last_dish.get(call.from_user.id)
    if not scaled:
        await call.answer("Блюдо не найдено, начни заново", show_alert=True)
        return

    add_food_log(
        call.from_user.id, meal_type, scaled["name"],
        scaled["weight"], scaled["calories"], scaled["protein"],
        scaled["fat"], scaled["carbs"],
    )
    user = get_user(call.from_user.id)
    totals = get_food_totals_today(call.from_user.id)
    left = user["daily_calories"] - totals["calories"]

    await call.message.edit_text(
        f"✅ **{scaled['name']}** добавлено в дневник\n\n"
        f"🔥 {scaled['calories']} ккал, {scaled['weight']} г\n\n"
        f"**За сегодня:** {int(totals['calories'])} / {user['daily_calories']} ккал\n"
        f"Осталось: **{int(left)} ккал**",
        parse_mode="Markdown",
    )
    await call.message.answer("Меню или дневник?", reply_markup=main_menu())


@router.callback_query(F.data == "cancel_dish")
async def cancel_dish(call: CallbackQuery):
    _last_dish.pop(call.from_user.id, None)
    await call.message.edit_text("❌ Отменено.")
    await call.message.answer("Что дальше?", reply_markup=main_menu())
