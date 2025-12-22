from telegram import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура"""
    keyboard = [
        [KeyboardButton("/new - Новая сессия")],
        [KeyboardButton("/help - Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отмены"""
    keyboard = [[KeyboardButton("❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)