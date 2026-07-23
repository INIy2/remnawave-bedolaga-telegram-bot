"""Билдер инфо-экрана «Помощь и контакты» (классический бот FreekVPN).

Чистая функция: получает готовые значения (тексты, контакты, ссылки, включены
ли тикеты) и возвращает caption + ряды кнопок. Не ходит в БД и не знает про
конфиг — резолв настроек делает хендлер show_info_menu.

Все каналы поддержки (бот/почта/тикет) и документы (политика/соглашение) собраны
на одном экране: текстом-ссылками плюс кнопки «Создать обращение» и документы.
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
    support_email: str = '',
    tickets_enabled: bool = False,
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

    support_lines: list[str] = []
    if support_url:
        username = (support_username or '').strip() or '@support'
        support_lines.append(
            texts.t(
                'INFO_HELP_SUPPORT_BOT_LINE',
                '• Поддержка бот: <a href="{url}">{username}</a>',
            ).format(url=support_url, username=username)
        )
    if support_email:
        support_lines.append(
            texts.t(
                'INFO_HELP_SUPPORT_EMAIL_LINE',
                '• Поддержка почта: <code>{email}</code>',
            ).format(email=support_email)
        )
    if tickets_enabled:
        support_lines.append(
            texts.t(
                'INFO_HELP_SUPPORT_TICKET_LINE',
                '• Поддержка c помощью тикета: Кнопка «Создать обращение»',
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

    if support_lines:
        caption += '\n\n' + '\n'.join(support_lines)
    if doc_lines:
        caption += '\n\n' + '\n'.join(doc_lines)

    rows: list[list[types.InlineKeyboardButton]] = []
    if tickets_enabled:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('INFO_MENU_CREATE_TICKET', 'Создать обращение'),
                callback_data='support_request',
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
