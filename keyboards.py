def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💧 Выпить воды")],
            [KeyboardButton(text="🍽 Меню")],
            [KeyboardButton(text="📝 Дневник еды")],
            [KeyboardButton(text="🔥 Тренировка")],
            [KeyboardButton(text="🤖 AI-помощник")],   # <-- новая кнопка
            [KeyboardButton(text="⚖️ Записать вес")],
            [KeyboardButton(text="📏 Замеры")],
            [KeyboardButton(text="📊 Прогресс")],
            [KeyboardButton(text="📈 График")],
            [KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="👤 Профиль")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
