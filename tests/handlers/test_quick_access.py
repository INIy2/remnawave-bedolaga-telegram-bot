from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import ReplyKeyboardRemove


def test_bot_commands_order_and_labels():
    from app.handlers.quick_access import get_bot_commands

    cmds = get_bot_commands('ru')
    assert [(c.command, c.description) for c in cmds] == [
        ('start', 'Главное меню'),
        ('connect', 'Как подключиться?'),
        ('pay', 'Оплатить'),
        ('referrals', 'Рефералы'),
        ('promo', 'Ввести промокод'),
        ('support', 'Поддержка'),
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

    # 6 команд (без /start — он в start.py) + 5 reply-кнопок = 11 регистраций.
    # Reply-хендлеры остались после отказа от клавиатуры: она ещё висит у тех,
    # у кого её не успели снять, и нажатия должны продолжать работать.
    assert dp.message.register.call_count == 11


def test_reply_button_text_variants_covers_all_languages(monkeypatch):
    from app.handlers import quick_access

    # эмулируем две локали: дефолт 'ru' и 'en' с переопределённым RK_CONNECT
    # (settings — pydantic-модель: instance-level monkeypatch на метод падает с
    # ValueError "object has no field", поэтому патчим на уровне класса)
    monkeypatch.setattr(type(quick_access.settings), 'get_available_languages', lambda self: ['ru', 'en'])

    real_get_texts = quick_access.get_texts

    class _T:
        def __init__(self, lang):
            self._lang = lang

        def t(self, key, default):
            if self._lang == 'en' and key == 'RK_CONNECT':
                return 'How to connect?'
            return real_get_texts('ru').t(key, default)

    monkeypatch.setattr(quick_access, 'get_texts', lambda lang='ru': _T(lang))

    variants = quick_access._reply_button_text_variants()
    assert 'Как подключиться?' in variants['connect']
    assert 'How to connect?' in variants['connect']


class _FakeCache:
    """Мини-Redis: connected=False эмулирует недоступный Redis (set → False)."""

    def __init__(self, connected: bool = True, initial: dict | None = None):
        self.connected = connected
        self.store: dict = dict(initial or {})

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, expire=None):
        if not self.connected:
            return False
        self.store[key] = value
        return True

    async def delete(self, key):
        self.store.pop(key, None)
        return True


def _rk_user(user_id: int = 44, language: str = 'ru'):
    return SimpleNamespace(id=user_id, language=language)


def _rk_bot(message_id: int = 500):
    bot = SimpleNamespace()
    bot.send_message = AsyncMock(return_value=SimpleNamespace(message_id=message_id))
    bot.delete_message = AsyncMock()
    return bot


@pytest.fixture
def rk_cache(monkeypatch):
    """Подменяет app.utils.cache.cache — импорт в функции идёт из модуля."""

    def _install(cache):
        import app.utils.cache as cache_module

        monkeypatch.setattr(cache_module, 'cache', cache)
        return cache

    return _install


@pytest.mark.asyncio
async def test_keyboard_removed_once_and_carrier_deleted(rk_cache):
    """Снятие идёт ровно один раз и убирает прежний носитель.

    От постоянной reply-клавиатуры отказались (8abb36d6), но persistent-клавиатура
    сама не исчезает — её надо явно снять. Прежний носитель удаляем: если он
    моложе 48ч, это уже сбрасывает клавиатуру у клиента.
    """
    from app.handlers.quick_access import RK_CARRIER_KEY, RK_REMOVED_KEY, remove_quick_reply_keyboard

    carrier_key = RK_CARRIER_KEY.format(user_id=44)
    cache = rk_cache(_FakeCache(initial={carrier_key: 300}))
    bot = _rk_bot(message_id=500)

    await remove_quick_reply_keyboard(bot, chat_id=777, db_user=_rk_user())

    # Носитель удалён, и следом — техническое сообщение с ReplyKeyboardRemove.
    assert [call.args for call in bot.delete_message.await_args_list] == [(777, 300), (777, 500)]
    assert isinstance(bot.send_message.await_args.kwargs['reply_markup'], ReplyKeyboardRemove)
    assert carrier_key not in cache.store
    assert cache.store[RK_REMOVED_KEY.format(user_id=44)] == 1


@pytest.mark.asyncio
async def test_removal_is_not_repeated(rk_cache):
    """Повторный /start не должен слать «⌨️» снова — флаг уже стоит."""
    from app.handlers.quick_access import RK_REMOVED_KEY, remove_quick_reply_keyboard

    rk_cache(_FakeCache(initial={RK_REMOVED_KEY.format(user_id=44): 1}))
    bot = _rk_bot()

    await remove_quick_reply_keyboard(bot, chat_id=777, db_user=_rk_user())

    bot.send_message.assert_not_awaited()
    bot.delete_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_removal_spam_when_redis_down(rk_cache):
    """Без Redis флаг не запоминается — слать ReplyKeyboardRemove на КАЖДЫЙ
    /start нельзя, поэтому выходим молча."""
    from app.handlers.quick_access import remove_quick_reply_keyboard

    rk_cache(_FakeCache(connected=False))
    bot = _rk_bot()

    await remove_quick_reply_keyboard(bot, chat_id=777, db_user=_rk_user())

    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_flag_released_when_send_fails(rk_cache):
    """Упавшая отправка не должна оставить юзера с висящей клавиатурой навсегда:
    флаг отпускаем, чтобы повторить на следующем /start."""
    from app.handlers.quick_access import RK_REMOVED_KEY, remove_quick_reply_keyboard

    cache = rk_cache(_FakeCache())
    bot = _rk_bot()
    bot.send_message = AsyncMock(side_effect=RuntimeError('telegram down'))

    with pytest.raises(RuntimeError):
        await remove_quick_reply_keyboard(bot, chat_id=777, db_user=_rk_user())

    assert RK_REMOVED_KEY.format(user_id=44) not in cache.store
