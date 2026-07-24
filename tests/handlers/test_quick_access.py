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


@pytest.mark.asyncio
async def test_adapter_answer_surfaces_alert_text():
    from app.handlers.quick_access import _MessageAsCallback

    placeholder = MagicMock()
    placeholder.edit_text = AsyncMock()
    adapter = _MessageAsCallback(placeholder, MagicMock(), MagicMock())

    # с текстом-алертом → редактируем placeholder
    await adapter.answer('Реферальная программа отключена', show_alert=True)
    placeholder.edit_text.assert_awaited_once_with('Реферальная программа отключена')

    # без текста → no-op (не трогаем placeholder повторно)
    placeholder.edit_text.reset_mock()
    await adapter.answer()
    placeholder.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_open_via_adapter_logo_mode(monkeypatch):
    from app.handlers import quick_access

    monkeypatch.setattr(quick_access.settings, 'ENABLE_LOGO_MODE', True, raising=False)
    import app.utils.message_patch as mp
    monkeypatch.setattr(mp, 'LOGO_PATH', SimpleNamespace(exists=lambda: True), raising=False)
    monkeypatch.setattr(mp, 'get_logo_media', lambda: 'LOGO', raising=False)

    placeholder = MagicMock(name='placeholder')
    source = MagicMock(name='source')
    source.answer_photo = AsyncMock(return_value=placeholder)
    source.answer = AsyncMock()
    source.from_user = MagicMock()
    handler = AsyncMock()

    await quick_access._open_via_adapter(source, MagicMock(), handler, db_user='U')

    source.answer_photo.assert_awaited_once()      # фото-placeholder
    source.answer.assert_not_awaited()             # текстовый путь не задействован
    assert handler.await_args.args[0].message is placeholder


@pytest.mark.asyncio
async def test_connect_routes_to_paywall_without_subscription(monkeypatch):
    from types import SimpleNamespace

    from app.handlers import quick_access

    calls = {}

    async def fake_open(source, bot, handler, **kwargs):
        calls['handler'] = handler
        calls['kwargs'] = kwargs

    monkeypatch.setattr(quick_access, '_open_via_adapter', fake_open)

    import app.handlers.subscription.purchase as purchase

    message = MagicMock()
    db_user = SimpleNamespace(subscriptions=[], language='ru')

    await quick_access._route_connect(message, bot='BOT', db_user=db_user, db='DB', state='ST')

    assert calls['handler'] is purchase.start_subscription_purchase
    assert calls['kwargs'] == {'state': 'ST', 'db_user': db_user, 'db': 'DB'}


@pytest.mark.asyncio
async def test_connect_routes_to_guide_with_subscription(monkeypatch):
    from types import SimpleNamespace

    from app.handlers import quick_access

    calls = {}

    async def fake_open(source, bot, handler, **kwargs):
        calls['handler'] = handler

    monkeypatch.setattr(quick_access, '_open_via_adapter', fake_open)

    import app.handlers.subscription.purchase as purchase

    message = MagicMock()
    db_user = SimpleNamespace(subscriptions=[SimpleNamespace(is_active=True, actual_status='active')], language='ru')

    await quick_access._route_connect(message, bot='BOT', db_user=db_user, db='DB', state='ST')

    assert calls['handler'] is purchase.show_install_guide_devices


def test_register_handlers_wires_commands_and_reply_buttons():
    from unittest.mock import MagicMock

    from app.handlers import quick_access

    dp = MagicMock()
    dp.message = MagicMock()
    dp.message.register = MagicMock()

    quick_access.register_handlers(dp)

    # 5 команд (без /start — он в start.py) + 5 reply-кнопок = 10 регистраций
    assert dp.message.register.call_count == 10
