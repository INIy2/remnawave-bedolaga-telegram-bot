"""Билдер экрана подключения (классический бот FreekVPN).

Чистая функция: получает готовые ссылки/настройки и возвращает caption + ряды
кнопок. Не ходит в БД и не знает про конфиг — резолв делает хендлер
show_install_guide_devices. Группировка по приложениям: Happ (Android/Windows)
и INCY (iPhone/iPad/macOS).
"""

from __future__ import annotations

from aiogram import types


def build_connect_screen(
    texts,
    *,
    happ_android_url: str = '',
    happ_windows_url: str = '',
    incy_url: str = '',
    subscription_link: str = '',
    happ_redirect_url: str = '',
    incy_redirect_url: str = '',
) -> tuple[str, list[list[types.InlineKeyboardButton]]]:
    header = texts.t('CONNECT_SCREEN_TITLE', '📲 <b>Подключение</b>')
    intro = texts.t('CONNECT_SCREEN_INTRO', 'Выбери приложение под свою платформу и подключись в один тап.')
    download = texts.t('CONNECT_SCREEN_DOWNLOAD', 'скачать')

    caption = header
    if intro:
        caption += f'\n\n{intro}'

    happ_lines: list[str] = []
    if happ_android_url:
        happ_lines.append(f'Android: <a href="{happ_android_url}">{download}</a>')
    if happ_windows_url:
        happ_lines.append(f'Windows: <a href="{happ_windows_url}">{download}</a>')
    if happ_lines:
        caption += '\n\n' + texts.t('CONNECT_SCREEN_HAPP', '<b>Happ</b> — Android, Windows')
        caption += '\n' + '\n'.join(happ_lines)

    if incy_url:
        caption += '\n\n' + texts.t('CONNECT_SCREEN_INCY', '<b>INCY</b> — iPhone/iPad, macOS')
        caption += '\n' + f'App Store: <a href="{incy_url}">{download}</a>'

    if subscription_link:
        caption += '\n\n' + texts.t(
            'CONNECT_SCREEN_COPY_HINT',
            '💡 Если кнопка ниже не сработала — скопируй ссылку и добавь вручную:',
        )
        caption += f'\n<blockquote expandable><code>{subscription_link}</code></blockquote>'

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
