"""Быстрый доступ: меню slash-команд + постоянная нижняя reply-клавиатура.

Кнопки/команды — тонкие обёртки над уже существующими экранами. Экраны,
реализованные как callback-хендлеры, вызываются через адаптер _MessageAsCallback:
он подставляет свежесозданное сообщение бота, которое существующий рендер
редактирует в целевой экран (edit_text / edit_or_answer_photo и т.п.).
"""

from __future__ import annotations

from contextlib import suppress

from aiogram.types import BotCommand, KeyboardButton, ReplyKeyboardMarkup

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


def get_bot_commands(language: str = 'ru') -> list[BotCommand]:
    texts = get_texts(language)
    return [
        BotCommand(command='start', description=texts.t('CMD_START', 'Главное меню')),
        BotCommand(command='connect', description=texts.t('CMD_CONNECT', 'Как подключиться?')),
        BotCommand(command='pay', description=texts.t('CMD_PAY', 'Оплатить')),
        BotCommand(command='referrals', description=texts.t('CMD_REFERRALS', 'Рефералы')),
        BotCommand(command='promo', description=texts.t('CMD_PROMO', 'Ввести промокод')),
        BotCommand(command='info', description=texts.t('CMD_INFO', 'Инфо')),
    ]


class _MessageAsCallback:
    """Минимальный адаптер: выдаёт себя за CallbackQuery для рендеров экранов.

    Рендеры используют .message (редактируют его), .from_user, .bot и awaitable
    .answer(...). Мы подставляем свежесозданное сообщение бота как .message.
    """

    def __init__(self, message, from_user, bot):
        self.message = message
        self.from_user = from_user
        self.bot = bot
        self.data = None

    async def answer(self, text: str | None = None, show_alert: bool = False, **kwargs):
        # На успешном пути рендер уже отредактировал .message в целевой экран, а
        # финальный callback.answer() без текста — просто закрывает "часики": no-op.
        # Но на ранних return-ветках хендлер отдаёт фидбек ТОЛЬКО через
        # answer(text, show_alert=True) и не трогает .message — тогда показываем
        # этот текст, чтобы не осталось висящего placeholder-сообщения.
        if text:
            with suppress(Exception):
                await self.message.edit_text(text)
        return None


async def _open_via_adapter(source_message, bot, handler, **kwargs) -> None:
    from app.utils.message_patch import LOGO_PATH, get_logo_media

    if settings.ENABLE_LOGO_MODE and LOGO_PATH.exists():
        placeholder = await source_message.answer_photo(get_logo_media(), caption='…')
    else:
        placeholder = await source_message.answer('…')

    adapter = _MessageAsCallback(placeholder, source_message.from_user, bot)
    await handler(adapter, **kwargs)


def _has_active_subscription(db_user) -> bool:
    """Проверить, есть ли у пользователя активная подписка.

    Подписка считается активной, если is_active=True ИЛИ actual_status='limited'.
    Зеркало логики из app/handlers/menu.py (lines 198-199).
    """
    subs = getattr(db_user, 'subscriptions', None) or []
    return any(
        getattr(s, 'is_active', False) or getattr(s, 'actual_status', None) == 'limited'
        for s in subs
    )


async def _route_connect(message, *, bot, db_user, db, state) -> None:
    from app.handlers.subscription.purchase import (
        show_install_guide_devices,
        start_subscription_purchase,
    )

    if _has_active_subscription(db_user):
        await _open_via_adapter(message, bot, show_install_guide_devices, db_user=db_user, db=db)
    else:
        await _open_via_adapter(message, bot, start_subscription_purchase, state=state, db_user=db_user, db=db)


async def _route_pay(message, *, bot, db_user, db, state) -> None:
    from app.handlers.subscription.purchase import start_subscription_purchase

    await _open_via_adapter(message, bot, start_subscription_purchase, state=state, db_user=db_user, db=db)


async def _route_referrals(message, *, bot, db_user, db) -> None:
    from app.handlers.referral import show_referral_info

    await _open_via_adapter(message, bot, show_referral_info, db_user=db_user, db=db)


async def _route_info(message, *, bot, db_user, db) -> None:
    from app.handlers.menu import show_info_menu

    await _open_via_adapter(message, bot, show_info_menu, db_user=db_user, db=db)


async def _route_support(message, *, bot, db_user) -> None:
    from app.handlers.support import show_support_info

    await _open_via_adapter(message, bot, show_support_info, db_user=db_user)


async def _route_promo(message, *, db_user, state) -> None:
    from app.keyboards.inline import get_back_keyboard
    from app.states import PromoCodeStates

    texts = get_texts(db_user.language)
    await message.answer(texts.PROMOCODE_ENTER, reply_markup=get_back_keyboard(db_user.language))
    await state.set_state(PromoCodeStates.waiting_for_code)
    await state.update_data(_prev_state=None, _prev_data={})


async def _route_doc(message, *, bot, db_user, db, url: str, label_key: str, label_default: str) -> None:
    """Документ (политика/соглашение): при наличии URL — сообщение со ссылкой-кнопкой,
    иначе фолбэк на инфо-экран (там документы показываются встроенно)."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    texts = get_texts(db_user.language)
    url = (url or '').strip()
    if not url:
        await _route_info(message, bot=bot, db_user=db_user, db=db)
        return

    label = texts.t(label_key, label_default)
    read = texts.t('INFO_HELP_READ', 'читать')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=read, url=url)]])
    await message.answer(label, reply_markup=kb)
