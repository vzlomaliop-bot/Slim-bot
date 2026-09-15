from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import (
    get_user, get_food_totals_today, get_food_today,
    add_food_log, clear_food_today,
)
from keyboards import main_menu, diary_menu_kb, diary_back_kb

router = Router()


class DiaryStates(StatesGroup):
    choosing_meal = State()
    entering_food = State()


@router.message(F.text == "📝 Дневник еды")
async def diary_menu(msg: Message):
    await msg.answer("Что делаем?", reply_markup=diary_menu_kb())


@router.message(F.text.in_(["🍳 Завтрак", "🍲 Обед", "🍽 Ужин", "🍎 Перекус"]))
async def diary_choose_meal(msg: Message, state: FSMContext):
    """Эту ветку обрабатывает diary, но только когда пользователь СНАЧАЛА нажал Дневник еды.
    Чтобы разделить с meals — используем отдельные кнопки для дневника."""
    # Разделение: кнопки дневника отличаются от кнопок меню
    # Если пользователь в диалоге дневника, бот попросит ввод продукта
    meal_map = {
        "🍳 Завтрак": "breakfast",
        "🍲 Обед": "lunch",
        "🍽 Ужин": "dinner",
        "🍎 Перекус": "snack",
    }
    meal_type = meal_map.get(msg.text)
    if not meal_type:
        return
    await state.update_data(meal_type=meal_type)
    await msg.answer(
        "Введи продукт и граммы так:\n\n"
        "**Название продукта / калории на 100г / белки / жиры / углеводы**\n\n"
        "Например: `Курица / 165 / 31 / 3.6 / 0`\n\n"
        "Потом бот спросит граммовку.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(DiaryStates.entering_food)


@router.message(DiaryStates.entering_food)
async def diary_enter_food(msg: Message, state: FSMContext):
    try:
        parts = msg.text.split("/")
        name = parts[0].strip()
        cal100, prot100, fat100, carb100 = [float(x.strip().replace(",", ".")) for x in parts[1:5]]
    except Exception:
        await msg.answer(
            "Формат: `Название / ккал_100 / белки / жиры / углеводы`",
            parse_mode="Markdown",
        )
        return
    await state.update_data(name=name, cal100=cal100, prot100=prot100,
                            fat100=fat100, carb100=carb100)
    await msg.answer(
        f"Сколько грамм **{name}** ты съел?\nНапример: `150`",
        parse_mode="Markdown",
    )
    await state.set_state(DiaryStates.choosing_meal)  # переиспользуем состояние


@router.message(DiaryStates.choosing_meal)
async def diary_enter_grams(msg: Message, state: FSMContext):
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

    add_food_log(
        msg.from_user.id, data["meal_type"], data["name"],
        grams, cal, prot, fat, carb,
    )
    await state.clear()

    user = get_user(msg.from_user.id)
    totals = get_food_totals_today(msg.from_user.id)
    left = user["daily_calories"] - totals["calories"]

    await msg.answer(
        f"✅ Добавлено: {data['name']} {grams}г\n"
        f"🔥 {cal} ккал | 🥩 {prot} | 🥑 {fat} | 🍚 {carb}\n\n"
        f"**За сегодня:** {int(totals['calories'])} / {user['daily_calories']} ккал\n"
        f"Осталось: **{int(left)} ккал**",
        reply_markup=diary_menu_kb(),
        parse_mode="Markdown",
    )


@router.message(F.text == "📋 Что я съел сегодня")
async def diary_today(msg: Message):
    user = get_user(msg.from_user.id)
    rows = get_food_today(msg.from_user.id)
    totals = get_food_totals_today(msg.from_user.id)

    if not rows:
        await msg.answer("Пока пусто. Начни с кнопки завтрак/обед/ужин.",
                         reply_markup=diary_menu_kb())
        return

    lines = ["📋 **Съедено сегодня:**\n"]
    for meal, name, grams, cal, prot, fat, carb in rows:
        lines.append(f"• [{meal}] {name} {grams}г — {int(cal)} ккал")

    lines.append("")
    lines.append(f"🔥 Итого: **{int(totals['calories'])}** / {user['daily_calories']} ккал")
    lines.append(f"🥩 Б: {int(totals['protein'])} г")
    lines.append(f"🥑 Ж: {int(totals['fat'])} г")
    lines.append(f"🍚 У: {int(totals['carbs'])} г")
    left = user["daily_calories"] - totals["calories"]
    if left > 0:
        lines.append(f"\n✅ Осталось: **{int(left)} ккал**")
    else:
        lines.append(f"\n⚠️ Перебор: **{int(-left)} ккал**")

    await msg.answer("\n".join(lines), reply_markup=diary_menu_kb(), parse_mode="Markdown")


@router.message(F.text == "🗑 Очистить день")
async def diary_clear(msg: Message):
    clear_food_today(msg.from_user.id)
    await msg.answer("Дневник за сегодня очищен.", reply_markup=diary_menu_kb())


@router.message(F.text == "⬅️ К дневнику")
async def diary_back(msg: Message):
    await msg.answer("Дневник еды:", reply_markup=diary_menu_kb())
