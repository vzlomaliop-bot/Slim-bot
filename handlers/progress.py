from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user_exercises, get_exercise_full

router = Router()


def _clean_name(ex_key):
    """Достаёт имя упражнения и отбрасывает мусор (None, пусто, разделители)."""
    if not ex_key:
        return None
    parts = ex_key.split("|")
    name = parts[-1].strip()
    if not name:
        return None
    if name.lower() in ("none", "null", "nan", "0"):
        return None
    return name


@router.callback_query(F.data == "progress")
async def progress_cb(call: CallbackQuery):
    exercises = get_user_exercises(call.from_user.id)

    # Чистим мусор и убираем дубли
    cleaned = []
    seen = set()
    for i, ex in enumerate(exercises):
        name = _clean_name(ex)
        if name and name not in seen:
            seen.add(name)
            cleaned.append((i, ex, name))

    if not cleaned:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="change_prog")]
        ])
        await call.message.edit_text(
            "📊 Пока нет записанных упражнений.\n\n"
            "Начни тренировку → данные появятся здесь.",
            reply_markup=kb,
        )
        return

    rows = [[InlineKeyboardButton(text=name, callback_data=f"ex_{idx}")]
            for idx, _, name in cleaned]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="change_prog")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await call.message.edit_text(
        f"📊 <b>Твой прогресс</b>\n\n"
        f"Выбери упражнение ({len(cleaned)} шт.):",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("ex_"))
async def show_exercise_history(call: CallbackQuery):
    try:
        idx = int(call.data.split("_", 1)[1])
    except (ValueError, IndexError):
        await call.answer("Ошибка")
        return

    exercises = get_user_exercises(call.from_user.id)
    if idx >= len(exercises):
        await call.answer("Не найдено", show_alert=True)
        return

    ex_key = exercises[idx]
    name = _clean_name(ex_key)
    if not name:
        await call.answer("Запись повреждена", show_alert=True)
        return

    rows = get_exercise_full(call.from_user.id, ex_key)
    if not rows:
        await call.answer("Нет данных", show_alert=True)
        return

    from collections import OrderedDict
    by_date = OrderedDict()
    for date, w, r, sn, day_name in rows:
        d = date[:10]
        if d not in by_date:
            by_date[d] = {"sets": [], "day": day_name or ""}
        by_date[d]["sets"].append((sn, w, r))

    max_w = max(r[1] for r in rows)
    last_w = rows[-1][1]
    last_r = rows[-1][2]
    total_sessions = len(by_date)

    lines = [
        f"📈 <b>{name}</b>",
        "",
        f"🔹 Рекорд: <b>{max_w} кг</b>",
        f"🔹 Последний: {last_w} кг × {last_r}",
        f"🔹 Тренировок: {total_sessions}",
        "",
        "<b>История:</b>",
    ]
    for d, data in by_date.items():
        sets_str = " • ".join(f"{w}×{r}" for _, w, r in data["sets"])
        day_label = f" <i>({data['day']})</i>" if data["day"] else ""
        lines.append(f"<code>{d}</code>{day_label}: {sets_str}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3900] + "\n...<i>(обрезано)</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К упражнениям", callback_data="progress")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
