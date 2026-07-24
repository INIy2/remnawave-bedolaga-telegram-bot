from aiogram.types import ReplyKeyboardMarkup

from app.handlers.quick_access import get_quick_reply_keyboard


def test_reply_keyboard_layout():
    kb = get_quick_reply_keyboard('ru')
    assert isinstance(kb, ReplyKeyboardMarkup)
    assert kb.is_persistent is True
    assert kb.resize_keyboard is True
    texts = [[btn.text for btn in row] for row in kb.keyboard]
    assert texts == [
        ['Как подключиться?', 'Ввести промокод'],
        ['Политика конфиденциальности', 'Пользовательское соглашение'],
        ['Поддержка'],
    ]
