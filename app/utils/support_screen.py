"""Билдер карточки «Служба поддержки» (классический бот FreekVPN).

Чистая функция: получает готовые настройки (username/url/email, включены ли
тикеты) и возвращает caption + ряды кнопок. Три канала как в веб-кабинете:
Telegram, email (копируемым текстом — Telegram не открывает mailto из кнопок)
и создание обращения (существующий флоу support_request → тикет).
"""

from __future__ import annotations

from aiogram import types


def build_support_screen(
    texts,
    *,
    support_username: str = '',
    support_url: str = '',
    support_email: str = '',
    tickets_enabled: bool = False,
) -> tuple[str, list[list[types.InlineKeyboardButton]]]:
    header = texts.t('SUPPORT_CARD_TITLE', '<b>Служба поддержки</b>')
    intro = texts.t(
        'SUPPORT_CARD_INTRO',
        'Возникли вопросы по подписке, оплате или подключению? Напишите нам удобным способом.',
    )
    caption = header
    if intro:
        caption += f'\n\n{intro}'

    lines: list[str] = []
    if support_url:
        username = (support_username or '').strip() or support_url
        lines.append(
            texts.t('SUPPORT_CARD_TELEGRAM', 'Telegram: {username}').format(username=username)
        )
    if support_email:
        lines.append(
            texts.t('SUPPORT_CARD_EMAIL', 'Электронная почта: <code>{email}</code>').format(email=support_email)
        )
    if tickets_enabled:
        lines.append(
            texts.t(
                'SUPPORT_CARD_TICKET',
                'Создать обращение: опишите проблему — обычно отвечаем в течение часа',
            )
        )
    if lines:
        caption += '\n\n' + '\n'.join(lines)

    rows: list[list[types.InlineKeyboardButton]] = []
    if support_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('SUPPORT_CARD_WRITE_BTN', 'Написать'),
                url=support_url,
            )
        ])
    if tickets_enabled:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('SUPPORT_CARD_TICKET_BTN', 'Создать обращение'),
                callback_data='support_request',
            )
        ])
    rows.append([
        types.InlineKeyboardButton(
            text=texts.t('MENU_BACK_BUTTON', '← Назад'),
            callback_data='menu_info',
        )
    ])
    return caption, rows
