from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💧 Выпить воды")],
            [KeyboardButton(text="🍽 Меню")],
            [KeyboardButton(text="📝 Дневник еды")],
            [KeyboardButton(text="🔥 Тренировка")],
            [KeyboardButton(text="⚖️ Записать вес")],
            [KeyboardButton(text="📏 Замеры")],
            [KeyboardButton(text="📊 Прогресс")],
            [KeyboardButton(text="📈 График")],
            [KeyboardButton(text="👤 Профиль")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def water_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="+250 мл"), KeyboardButton(text="+500 мл")],
            [KeyboardButton(text="+750 мл"), KeyboardButton(text="+1000 мл")],
            [KeyboardButton(text="⬅️ В меню")],
        ],
        resize_keyboard=True,
    )


def weigh_type_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌅 Натощак (утро)")],
            [KeyboardButton(text="🌙 Перед сном")],
            [KeyboardButton(text="⬅️ В меню")],
        ],
        resize_keyboard=True,
    )


def onboard_gender_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Мужской"), KeyboardButton(text="👩 Женский")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def onboard_activity_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🪑 Малоподвижный")],
            [KeyboardButton(text="🚶 Средний (3-4 трен/нед)")],
            [KeyboardButton(text="🏃 Высокий (5+ трен/нед)")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def meals_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍳 Завтрак"), KeyboardButton(text="🍲 Обед")],
            [KeyboardButton(text="🍽 Ужин")],
            [KeyboardButton(text="⬅️ В меню")],
        ],
        resize_keyboard=True,
    )


def dishes_kb(dishes):
    rows = []
    for d in dishes:
        rows.append([KeyboardButton(text=f"{d[2]}")])
    rows.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def dish_preview_kb(meal_type):
    """Inline-кнопки под предпросмотром блюда."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 В дневник", callback_data=f"add_dish_{meal_type}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_dish"),
        ],
    ])


def diary_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍳 Завтрак"), KeyboardButton(text="🍲 Обед")],
            [KeyboardButton(text="🍽 Ужин"), KeyboardButton(text="🍎 Перекус")],
            [KeyboardButton(text="📋 Что я съел сегодня")],
            [KeyboardButton(text="↩️ Удалить последнее")],
            [KeyboardButton(text="🗑 Очистить день")],
            [KeyboardButton(text="⬅️ В меню")],
        ],
        resize_keyboard=True,
    )


def confirm_cancel_kb():
    """Inline-кнопки подтверждения/отмены для ручного ввода."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Добавить", callback_data="confirm_add"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add"),
        ],
    ])


def charts_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📉 Вес (30 дней)")],
            [KeyboardButton(text="📉 Вес (90 дней)")],
            [KeyboardButton(text="📉 Вес (всё время)")],
            [KeyboardButton(text="⬅️ В меню")],
        ],
        resize_keyboard=True,
    )
