"""Билдер инфо-экрана «Помощь и контакты» (классический бот FreekVPN).

Чистая функция: получает готовые значения (тексты, контакт, ссылки) и
возвращает caption + ряды кнопок. Не ходит в БД и не знает про конфиг —
резолв настроек делает хендлер show_info_menu.
"""

from __future__ import annotations

from aiogram import types


def build_help_contacts_screen(
    texts,
    *,
    support_username: str,
    support_url: str,
    privacy_url: str,
    agreement_url: str,
) -> tuple[str, list[list[types.InlineKeyboardButton]]]:
    header = texts.t('INFO_HELP_HEADER', '💡 <b>Помощь и контакты</b>')
    intro = texts.t(
        'INFO_HELP_INTRO',
        'Если что-то непонятно — здесь все быстрые ссылки.',
    )
    read = texts.t('INFO_HELP_READ', 'читать')

    caption = header
    if intro:
        caption += f'\n<blockquote>{intro}</blockquote>'

    contact_lines: list[str] = []
    if support_url:
        username = (support_username or '').strip() or '@support'
        contact_lines.append(
            texts.t(
                'INFO_HELP_SUPPORT_LINE',
                '• Поддержка: <a href="{url}">{username}</a>',
            ).format(url=support_url, username=username)
        )
    contact_lines.append(
        texts.t(
            'INFO_HELP_CABINET_LINE',
            '• Кабинет: подписка, баланс и установка — в главном меню',
        )
    )

    doc_lines: list[str] = []
    if privacy_url:
        doc_lines.append(
            texts.t(
                'INFO_HELP_PRIVACY_LINE',
                '• Политика конфиденциальности: <a href="{url}">{read}</a>',
            ).format(url=privacy_url, read=read)
        )
    if agreement_url:
        doc_lines.append(
            texts.t(
                'INFO_HELP_AGREEMENT_LINE',
                '• Пользовательское соглашение: <a href="{url}">{read}</a>',
            ).format(url=agreement_url, read=read)
        )

    if contact_lines:
        caption += '\n\n' + '\n'.join(contact_lines)
    if doc_lines:
        caption += '\n\n' + '\n'.join(doc_lines)

    rows: list[list[types.InlineKeyboardButton]] = []
    if support_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('INFO_MENU_SUPPORT', 'Поддержка'),
                url=support_url,
            )
        ])
    if privacy_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('INFO_MENU_PRIVACY', 'Политика конфиденциальности'),
                url=privacy_url,
            )
        ])
    if agreement_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('INFO_MENU_AGREEMENT', 'Пользовательское соглашение'),
                url=agreement_url,
            )
        ])
    rows.append([
        types.InlineKeyboardButton(
            text=texts.t('MENU_BACK_BUTTON', '← Назад'),
            callback_data='back_to_menu',
        )
    ])

    return caption, rows
