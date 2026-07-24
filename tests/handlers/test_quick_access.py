from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
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


def test_bot_commands_order_and_labels():
    from app.handlers.quick_access import get_bot_commands

    cmds = get_bot_commands('ru')
    assert [(c.command, c.description) for c in cmds] == [
        ('start', 'Главное меню'),
        ('connect', 'Как подключиться?'),
        ('pay', 'Оплатить'),
        ('referrals', 'Рефералы'),
        ('promo', 'Ввести промокод'),
        ('info', 'Инфо'),
    ]


def test_has_active_subscription():
    from app.handlers.quick_access import _has_active_subscription

    active = SimpleNamespace(is_active=True, actual_status='active')
    limited = SimpleNamespace(is_active=False, actual_status='limited')
    expired = SimpleNamespace(is_active=False, actual_status='expired')

    assert _has_active_subscription(SimpleNamespace(subscriptions=[active])) is True
    assert _has_active_subscription(SimpleNamespace(subscriptions=[limited])) is True
    assert _has_active_subscription(SimpleNamespace(subscriptions=[expired])) is False
    assert _has_active_subscription(SimpleNamespace(subscriptions=[])) is False
    assert _has_active_subscription(SimpleNamespace(subscriptions=None)) is False


@pytest.mark.asyncio
async def test_open_via_adapter_text_mode(monkeypatch):
    from app.handlers import quick_access

    monkeypatch.setattr(quick_access.settings, 'ENABLE_LOGO_MODE', False, raising=False)

    placeholder = MagicMock(name='placeholder')
    source = MagicMock(name='source_message')
    source.answer = AsyncMock(return_value=placeholder)
    source.from_user = MagicMock()
    bot = MagicMock()

    handler = AsyncMock()

    await quick_access._open_via_adapter(source, bot, handler, db_user='U', db='DB')

    source.answer.assert_awaited_once()  # текстовый placeholder отправлен
    handler.assert_awaited_once()
    adapter = handler.await_args.args[0]
    assert adapter.message is placeholder
    assert adapter.bot is bot
    assert handler.await_args.kwargs == {'db_user': 'U', 'db': 'DB'}
    await adapter.answer()  # awaitable no-op
