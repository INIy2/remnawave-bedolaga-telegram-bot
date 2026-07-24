"""Быстрый доступ: меню slash-команд + постоянная нижняя reply-клавиатура.

Кнопки/команды — тонкие обёртки над уже существующими экранами. Экраны,
реализованные как callback-хендлеры, вызываются через адаптер _MessageAsCallback:
он подставляет свежесозданное сообщение бота, которое существующий рендер
редактирует в целевой экран (edit_text / edit_or_answer_photo и т.п.).
"""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.config import settings
from app.localization.texts import get_texts


def _reply_button_texts(texts) -> dict[str, str]:
    """Единый источник подписей reply-кнопок (клавиатура и матчинг хендлеров)."""
    return {
        'connect': texts.t('RK_CONNECT', 'Как подключиться?'),
        'promo': texts.t('RK_PROMO', 'Ввести промокод'),
        'privacy': texts.t('RK_PRIVACY', 'Политика конфиденциальности'),
        'agreement': texts.t('RK_AGREEMENT', 'Пользовательское соглашение'),
        'support': texts.t('RK_SUPPORT', 'Поддержка'),
    }


def get_quick_reply_keyboard(language: str = 'ru') -> ReplyKeyboardMarkup:
    t = _reply_button_texts(get_texts(language))
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t['connect']), KeyboardButton(text=t['promo'])],
            [KeyboardButton(text=t['privacy']), KeyboardButton(text=t['agreement'])],
            [KeyboardButton(text=t['support'])],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
