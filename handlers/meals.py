from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import (
    get_user, get_dishes, get_dish_by_name,
    add_food_log, get_food_totals_today,
)
from keyboards import (
    main_menu, meals_menu_kb, dishes_kb, dish_preview_kb,
    diary_menu_kb,
)
from meals_data import scale_dish

router = Router()

_last_dish = {}


class CustomDish(StatesGroup):
    entering_macros = State()
    entering_grams = State()
    choosing_meal = State()


MEAL_CHOICES = {
    "📝 Завтрак": ("breakfast", "Завтрак"),
    "📝 Обед": ("lunch", "Обед"),
    "📝 Ужин": ("dinner", "Ужин"),
    "📝 Перекус": ("snack", "Перекус"),
}


@router.message(F.text == "🍽 Меню")
async def meals_menu(msg: Message, state: FSMContext):
    await state.clear()
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


@router.message(F.text == "⬅️ Назад")
async def dishes_back(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Выбери приём пищи:", reply_markup=meals_menu_kb())


# ===== СВОЁ БЛЮДО =====

@router.message(F.text == "✏️ Своё блюдо")
async def custom_dish_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "✏️ **Своё блюдо**\n\n"
        "**Шаг 1 из 3.** Введи БЖУ продукта на 100 г через пробел:\n"
        "`белки жиры углеводы`\n\n"
        "Например: `31 3.6 0` — курица\n"
        "Или: `12.6 3.3 62` — гречка\n\n"
        "Калории бот посчитает сам.\n\n"
        "Отмена — ⬅️ Назад.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(CustomDish.entering_macros)


@router.message(CustomDish.entering_macros)
async def custom_enter_macros(msg: Message, state: FSMContext):
    if msg.text in ("⬅️ Назад", "⬅️ В меню"):
        await state.clear()
        await msg.answer("Отменено.", reply_markup=meals_menu_kb())
        return

    try:
        parts = msg.text.replace(",", ".").split()
        prot, fat, carb = [float(x) for x in parts[:3]]
        assert 0 <= prot <= 100 and 0 <= fat <= 100 and 0 <= carb <= 100
    except:
        await msg.answer(
            "❌ Формат: `белки жиры углеводы` через пробел.\n"
            "Пример: `31 3.6 0`",
            parse_mode="Markdown",
        )
        return

    cal_per100 = round(4 * prot + 9 * fat + 4 * carb, 1)
    await state.update_data(prot100=prot, fat100=fat, carb100=carb,
                            cal100=cal_per100)
    await msg.answer(
        f"✅ БЖУ на 100 г:\n"
        f"Б: {prot} | Ж: {fat} | У: {carb}\n"
        f"Калорийность: **~{cal_per100} ккал / 100 г**\n\n"
        f"**Шаг 2 из 3.** Сколько грамм?\n"
        f"Например: `150`",
        parse_mode="Markdown",
    )
    await state.set_state(CustomDish.entering_grams)


@router.message(CustomDish.entering_grams)
async def custom_enter_grams(msg: Message, state: FSMContext):
    if msg.text in ("⬅️ Назад", "⬅️ В меню"):
        await state.clear()
        await msg.answer("Отменено.", reply_markup=meals_menu_kb())
        return

    try:
        grams = float(msg.text.replace(",", ".").strip())
        assert 1 <= grams <= 3000
    except:
        await msg.answer("Введи граммы числом (например 150).")
        return

    data = await state.get_data()
    k = grams / 100
    cal = round(data["cal100"] * k, 1)
    prot = round(data["prot100"] * k, 1)
    fat = round(data["fat100"] * k, 1)
    carb = round(data["carb100"] * k, 1)

    await state.update_data(
        pending_grams=grams, pending_cal=cal, pending_prot=prot,
        pending_fat=fat, pending_carb=carb,
    )

    await msg.answer(
        f"🔎 **Предпросмотр**\n\n"
        f"**Своё блюдо** — {grams} г\n\n"
        f"🔥 {cal} ккал\n"
        f"🥩 Б: {prot} г\n"
        f"🥑 Ж: {fat} г\n"
        f"🍚 У: {carb} г\n\n"
        f"**Шаг 3 из 3.** В какой приём пищи добавить?",
        reply_markup=diary_menu_kb(),
        parse_mode="Markdown",
    )
    await state.set_state(CustomDish.choosing_meal)


@router.message(CustomDish.choosing_meal, F.text.in_(list(MEAL_CHOICES.keys())))
async def custom_choose_meal(msg: Message, state: FSMContext):
    data = await state.get_data()
    if "pending_cal" not in data:
        await msg.answer("Что-то потерялось, начни заново.")
        await state.clear()
        return

    meal_type, meal_label = MEAL_CHOICES[msg.text]
    add_food_log(
        msg.from_user.id, meal_type, "Своё блюдо",
        data["pending_grams"], data["pending_cal"], data["pending_prot"],
        data["pending_fat"], data["pending_carb"],
    )
    await state.clear()

    user = get_user(msg.from_user.id)
    totals = get_food_totals_today(msg.from_user.id)
    left = user["daily_calories"] - totals["calories"]

    await msg.answer(
        f"✅ **Своё блюдо** {data['pending_grams']} г → {meal_label}\n\n"
        f"🔥 {data['pending_cal']} ккал | 🥩 {data['pending_prot']} | "
        f"🥑 {data['pending_fat']} | 🍚 {data['pending_carb']}\n\n"
        f"**За сегодня:** {int(totals['calories'])} / {user['daily_calories']} ккал\n"
        f"Осталось: **{int(left)} ккал**",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


# ===== ГОТОВЫЕ БЛЮДА =====

@router.message(F.text.regexp(r"^[А-ЯЁа-яё].+$"))
async def dish_preview(msg: Message):
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
