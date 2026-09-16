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
    entering_macros = State()
    entering_grams = State()


MEAL_MAP = {
    "🍳 Завтрак": ("breakfast", "Завтрак"),
    "🍲 Обед": ("lunch", "Обед"),
    "🍽 Ужин": ("dinner", "Ужин"),
    "🍎 Перекус": ("snack", "Перекус"),
}


@router.message(F.text == "📝 Дневник еды")
async def diary_menu(msg: Message):
    await msg.answer(
        "**Дневник еды**\n\n"
        "Выбери приём пищи — бот попросит БЖУ продукта на 100 г.\n\n"
        "**Как вводить своё блюдо:**\n"
        "1. Жми на приём пищи (Завтрак / Обед / Ужин / Перекус)\n"
        "2. Введи БЖУ через пробел: `31 3.6 0` (белки / жиры / углеводы)\n"
        "3. Введи граммы порции: `150`\n"
        "4. Подтверди в предпросмотре\n\n"
        "Калории бот считает сам.",
        reply_markup=diary_menu_kb(),
        parse_mode="Markdown",
    )


@router.message(F.text.in_(list(MEAL_MAP.keys())))
async def diary_choose_meal(msg: Message, state: FSMContext):
    current = await state.get_state()
    if current in (DiaryStates.entering_macros, DiaryStates.entering_grams):
        await msg.answer("Сейчас введи данные, как просил бот, или нажми ⬅️ В меню.")
        return

    meal_type, meal_label = MEAL_MAP[msg.text]
    await state.update_data(meal_type=meal_type, meal_label=meal_label)
    await msg.answer(
        f"**{meal_label}**\n\n"
        "Введи **БЖУ продукта на 100 г** через пробел:\n"
        "`белки жиры углеводы`\n\n"
        "Например, для курицы: `31 3.6 0`\n"
        "Для гречки: `12.6 3.3 62`\n"
        "Для яйца: `13 11 1`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.set_state(DiaryStates.entering_macros)


@router.message(DiaryStates.entering_macros)
async def diary_enter_macros(msg: Message, state: FSMContext):
    if msg.text in ("⬅️ В меню", "⬅️ К дневнику"):
        await state.clear()
        await msg.answer("Отменено.", reply_markup=diary_menu_kb())
        return

    try:
        parts = msg.text.replace(",", ".").split()
        prot, fat, carb = [float(x) for x in parts[:3]]
        assert 0 <= prot <= 100 and 0 <= fat <= 100 and 0 <= carb <= 100
    except:
        await msg.answer(
            "Формат: `белки жиры углеводы` через пробел.\n"
            "Например: `31 3.6 0`",
            parse_mode="Markdown",
        )
        return

    cal_per100 = round(4 * prot + 9 * fat + 4 * carb, 1)
    await state.update_data(prot100=prot, fat100=fat, carb100=carb,
                            cal100=cal_per100)
    await msg.answer(
        f"✅ БЖУ сохранено:\n"
        f"Б: {prot} г | Ж: {fat} г | У: {carb} г\n"
        f"Калорийность: **~{cal_per100} ккал / 100 г**\n\n"
        f"Теперь введи **граммы** порции. Например: `150`",
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

    await state.update_data(
        pending_grams=grams, pending_cal=cal, pending_prot=prot,
        pending_fat=fat, pending_carb=carb,
    )

    await msg.answer(
        f"🔎 **Предпросмотр**\n\n"
        f"Своё блюдо — {grams} г\n\n"
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
        call.from_user.id, data["meal_type"], "Своё блюдо",
        data["pending_grams"], data["pending_cal"], data["pending_prot"],
        data["pending_fat"], data["pending_carb"],
    )
    await state.clear()

    user = get_user(call.from_user.id)
    totals = get_food_totals_today(call.from_user.id)
    left = user["daily_calories"] - totals["calories"]

    await call.message.edit_text(
        f"✅ Добавлено: **Своё блюдо** {data['pending_grams']} г\n"
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
