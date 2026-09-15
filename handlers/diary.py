from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import (
    get_user, get_food_totals_today, get_food_today,
    add_food_log, clear_food_today, delete_last_food,
)
from keyboards import (
    main_menu, diary_menu_kb, confirm_cancel_kb,
)

router = Router()


class DiaryStates(StatesGroup):
    entering_food = State()
    entering_grams = State()


MEAL_MAP = {
    "🍳 Завтрак": ("breakfast", "Завтрак"),
    "🍲 Обед": ("lunch", "Обед"),
    "🍽 Ужин": ("dinner", "Ужин"),
    "🍎 Перекус": ("snack", "Перекус"),
}


@router.message(F.text == "📝 Дневник еды")
async def diary_menu(msg: Message):
    await msg.answer("Что делаем?", reply_markup=diary_menu_kb())


@router.message(F.text.in_(list(MEAL_MAP.keys())))
async def diary_choose_meal(msg: Message, state: FSMContext):
    # Если пользователь не начинал дневник — не реагируем (это меню "Меню" блюда).
    # Проверка: у пользователя должен быть активный диалог.
    # Различить сложно, поэтому используем текущее состояние.
    current = await state.get_state()

    # Пользователь только что нажал "📝 Дневник еды" → должен быть выбор блюда.
    # Если состояние не пустое и ожидает ввода граммов — обработаем ниже в diary_enter_grams.
    if current == DiaryStates.entering_grams:
        # Пользователь вместо граммов нажал на приём пищи — игнорируем
        await msg.answer("Сейчас введи граммы числом, например 150.")
        return

    meal_type, meal_label = MEAL_MAP[msg.text]
    await state.update_data(meal_type=meal_type, meal_label=meal_label)
    await msg.answer(
        f"**{meal_label}**\n\n"
        "Введи продукт в формате:\n"
        "`Название / ккал на 100г / белки / жиры / углеводы`\n\n"
        "Например: `Курица / 165 / 31 / 3.6 / 0`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(DiaryStates.entering_food)


@router.message(DiaryStates.entering_food)
async def diary_enter_food(msg: Message, state: FSMContext):
    # Отмена
    if msg.text in ("⬅️ В меню", "⬅️ К дневнику"):
        await state.clear()
        await msg.answer("Отменено.", reply_markup=diary_menu_kb())
        return

    try:
        parts = msg.text.split("/")
        name = parts[0].strip()
        cal100, prot100, fat100, carb100 = [float(x.strip().replace(",", ".")) for x in parts[1:5]]
    except Exception:
        await msg.answer(
            "Формат: `Название / ккал_100 / белки / жиры / углеводы`\n\n"
            "Или нажми ⬅️ В меню чтобы отменить.",
            parse_mode="Markdown",
        )
        return
    await state.update_data(name=name, cal100=cal100, prot100=prot100,
                            fat100=fat100, carb100=carb100)
    await msg.answer(
        f"Сколько грамм **{name}**?\nНапример: `150`\n\n"
        f"Или нажми ⬅️ В меню чтобы отменить.",
        parse_mode="Markdown",
    )
    await state.set_state(DiaryStates.entering_grams)


@router.message(DiaryStates.entering_grams)
async def diary_enter_grams(msg: Message, state: FSMContext):
    if msg.text in ("⬅️ В меню", "⬅️ К дневнику"):
        await state.clear()
        await msg.answer("Отменено.", reply_markup=diary_menu_kb())
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

    # Сохраняем в state данные для подтверждения
    await state.update_data(
        pending_grams=grams, pending_cal=cal, pending_prot=prot,
        pending_fat=fat, pending_carb=carb,
    )

    await msg.answer(
        f"🔎 **Предпросмотр**\n\n"
        f"**{data['name']}** — {grams} г\n\n"
        f"🔥 {cal} ккал\n"
        f"🥩 Б: {prot} г\n"
        f"🥑 Ж: {fat} г\n"
        f"🍚 У: {carb} г\n\n"
        f"Добавить в **{data['meal_label']}**?",
        reply_markup=confirm_cancel_kb(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "confirm_add")
async def confirm_add(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "pending_cal" not in data:
        await call.answer("Устарело", show_alert=True)
        return

    add_food_log(
        call.from_user.id, data["meal_type"], data["name"],
        data["pending_grams"], data["pending_cal"], data["pending_prot"],
        data["pending_fat"], data["pending_carb"],
    )
    await state.clear()

    user = get_user(call.from_user.id)
    totals = get_food_totals_today(call.from_user.id)
    left = user["daily_calories"] - totals["calories"]

    await call.message.edit_text(
        f"✅ Добавлено: **{data['name']}** {data['pending_grams']}г\n"
        f"🔥 {data['pending_cal']} ккал | 🥩 {data['pending_prot']} | "
        f"🥑 {data['pending_fat']} | 🍚 {data['pending_carb']}\n\n"
        f"**За сегодня:** {int(totals['calories'])} / {user['daily_calories']} ккал\n"
        f"Осталось: **{int(left)} ккал**",
        parse_mode="Markdown",
    )
    await call.message.answer("Что дальше?", reply_markup=diary_menu_kb())


@router.callback_query(F.data == "cancel_add")
async def cancel_add(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Отменено.")
    await call.message.answer("Что дальше?", reply_markup=diary_menu_kb())


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


@router.message(F.text == "↩️ Удалить последнее")
async def diary_undo(msg: Message):
    delete_last_food(msg.from_user.id)
    await msg.answer("Последняя запись удалена.", reply_markup=diary_menu_kb())


@router.message(F.text == "🗑 Очистить день")
async def diary_clear(msg: Message):
    clear_food_today(msg.from_user.id)
    await msg.answer("Дневник за сегодня очищен.", reply_markup=diary_menu_kb())


@router.message(F.text == "⬅️ К дневнику")
async def diary_back(msg: Message):
    await msg.answer("Дневник еды:", reply_markup=diary_menu_kb())
