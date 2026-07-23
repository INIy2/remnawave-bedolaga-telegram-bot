"""Билдер экрана подключения (классический бот FreekVPN).

Чистая функция: получает готовые ссылки/настройки и возвращает caption + ряды
кнопок. Не ходит в БД и не знает про конфиг — резолв делает хендлер
show_install_guide_devices. Группировка по приложениям: Happ и INCY, у каждого —
свои ссылки на платформы (показываются только заданные). Для Windows-ссылок
добавляется подсказка, какой именно файл скачивать.
"""

from __future__ import annotations

import html

from aiogram import types


def build_connect_screen(
    texts,
    *,
    happ_android_url: str = '',
    happ_windows_url: str = '',
    incy_url: str = '',
    incy_android_url: str = '',
    incy_windows_url: str = '',
    subscription_link: str = '',
    happ_redirect_url: str = '',
    incy_redirect_url: str = '',
) -> tuple[str, list[list[types.InlineKeyboardButton]]]:
    header = texts.t('CONNECT_SCREEN_TITLE', '📲 <b>Подключение</b>')
    intro = texts.t('CONNECT_SCREEN_INTRO', 'Выбери приложение под свою платформу и подключись в один тап.')
    download = texts.t('CONNECT_SCREEN_DOWNLOAD', 'скачать')
    happ_win_note = texts.t('CONNECT_HAPP_WIN_NOTE', 'нужен файл setup-Happ.x64.exe')
    incy_win_note = texts.t('CONNECT_INCY_WIN_NOTE', 'нужен файл incy-windows-setup.exe')

    caption = header
    if intro:
        caption += f'\n\n{intro}'

    def _app_block(name: str, entries: list[tuple[str, str, str, str]]) -> str:
        """entries: (suffix_label, line_label, url, note). Пустые url пропускаются."""
        present = [(suffix, line, url, note) for suffix, line, url, note in entries if url]
        if not present:
            return ''
        suffix = ', '.join(s for s, _, _, _ in present)
        block = f'\n\n<b>{name}</b> — {suffix}'
        for _, line_label, url, note in present:
            line = f'\n{line_label}: <a href="{html.escape(url, quote=True)}">{download}</a>'
            if note:
                line += f' — {note}'
            block += line
        return block

    caption += _app_block(
        'Happ',
        [
            ('Android', 'Android', happ_android_url, ''),
            ('Windows', 'Windows', happ_windows_url, happ_win_note),
        ],
    )
    caption += _app_block(
        'INCY',
        [
            ('iPhone/iPad, macOS', 'App Store', incy_url, ''),
            ('Android', 'Android', incy_android_url, ''),
            ('Windows', 'Windows', incy_windows_url, incy_win_note),
        ],
    )

    if subscription_link:
        caption += '\n\n' + texts.t(
            'CONNECT_SCREEN_COPY_HINT',
            '💡 Когда вы скачаете приложение, нажмите на подключение к нему. '
            'Если кнопка не работает, скопируйте ссылку и вставьте в приложение:',
        )
        caption += f'\n<blockquote expandable><code>{html.escape(subscription_link)}</code></blockquote>'

    rows: list[list[types.InlineKeyboardButton]] = []
    if happ_redirect_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('CONNECT_SCREEN_HAPP_BTN', '🔌 Подключить через Happ'),
                url=happ_redirect_url,
            )
        ])
    if incy_redirect_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('CONNECT_SCREEN_INCY_BTN', '🔌 Подключить через INCY'),
                url=incy_redirect_url,
            )
        ])
    rows.append([
        types.InlineKeyboardButton(
            text=texts.t('BACK_TO_MAIN_MENU_BUTTON', '⬅️ В главное меню'),
            callback_data='back_to_menu',
        )
    ])
    return caption, rows
