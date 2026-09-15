from datetime import date

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile

from database import get_user, get_weights, get_last_weight
from keyboards import main_menu, charts_menu_kb
from charts import build_weight_chart

router = Router()


@router.message(F.text == "📊 Прогресс")
async def progress(msg: Message):
    user = get_user(msg.from_user.id)
    fasted = get_weights(msg.from_user.id, "fasted", 90)
    last_fed = get_last_weight(msg.from_user.id, "fed")

    lines = ["📊 **Твой прогресс**\n"]

    if user:
        lost = round(user["start_weight"] - user["current_weight"], 1)
        left = round(user["current_weight"] - user["goal_weight"], 1)
        lines.append(f"🎯 {user['start_weight']} → {user['goal_weight']} кг")
        lines.append(f"📉 Сброшено: **{lost} кг**")
        lines.append(f"⏳ Осталось: **{left} кг**")
        lines.append("")

    if fasted:
        lines.append("🌅 **Натощак (последние):**")
        for d, w in fasted[-7:]:
            lines.append(f"• {d}: {w} кг")
        lines.append("")
    else:
        lines.append("🌅 Натощак: пока пусто\n")

    if last_fed:
        lines.append(f"🌙 Перед сном: {last_fed[0]}: {last_fed[1]} кг")
        lines.append("")

    if len(fasted) >= 2:
        try:
            first_d, first_w = fasted[0]
            last_d, last_w = fasted[-1]
            d1 = date.fromisoformat(first_d)
            d2 = date.fromisoformat(last_d)
            days = (d2 - d1).days
            if days > 0:
                diff = round(first_w - last_w, 2)
                per_week = round(diff / days * 7, 2)
                if diff > 0:
                    lines.append(f"📉 Тренд: {per_week:+.2f} кг/нед — худеешь!")
                elif diff < 0:
                    lines.append(f"📈 Тренд: {per_week:+.2f} кг/нед — вес растёт")
                else:
                    lines.append("➖ Тренд: 0 кг/нед — держишься")

                if per_week > 0 and user:
                    left_now = user["current_weight"] - user["goal_weight"]
                    if left_now > 0:
                        weeks = left_now / per_week
                        if weeks < 52:
                            lines.append(f"🎯 Прогноз: ~{int(weeks)} нед до цели")
        except Exception:
            pass

    await msg.answer("\n".join(lines), reply_markup=main_menu(), parse_mode="Markdown")


@router.message(F.text == "📈 График")
async def chart_menu(msg: Message):
    await msg.answer("Выбери диапазон:", reply_markup=charts_menu_kb())


@router.message(F.text.in_(["📉 Вес (30 дней)", "📉 Вес (90 дней)", "📉 Вес (всё время)"]))
async def chart_draw(msg: Message):
    user = get_user(msg.from_user.id)
    if "30" in msg.text:
        limit = 30
        title = "Вес — 30 дней"
    elif "90" in msg.text:
        limit = 90
        title = "Вес — 90 дней"
    else:
        limit = 365
        title = "Вес — вся история"

    weights = get_weights(msg.from_user.id, "fasted", limit)
    if len(weights) < 2:
        await msg.answer("Пока мало данных. Запиши минимум 2 замера натощак.")
        return

    goal = user["goal_weight"] if user else None
    buf = build_weight_chart(weights, goal=goal, title=title)
    if not buf:
        await msg.answer("Не удалось построить график.")
        return

    photo = BufferedInputFile(buf.read(), filename="chart.png")
    await msg.answer_photo(photo, caption=f"📉 {title}")
