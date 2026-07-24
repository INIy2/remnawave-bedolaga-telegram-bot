# Быстрый доступ: меню команд + нижняя reply-клавиатура — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в бота FreekVPN меню slash-команд и постоянную нижнюю reply-клавиатуру (2 колонки), которые открывают существующие экраны без дубля логики.

**Architecture:** Новый модуль `app/handlers/quick_access.py`. Reply-кнопки/команды — тонкие обёртки: экраны, уже реализованные как callback-хендлеры, вызываются из message-входа через маленький адаптер `_MessageAsCallback` (подставляет свежесозданное сообщение бота, которое существующий рендер редактирует в целевой экран). Чистые вещи (raw-ссылки на документы, промо-флоу) шлются напрямую. Команды регистрируются через `bot.set_my_commands`. Клавиатура «ставится» одним сообщением в начале `/start`.

**Tech Stack:** Python 3.13, aiogram 3, pytest. Тесты: `py -3.13 -m pytest` (system python 3.10 не тянет conftest).

**Spec:** `docs/superpowers/specs/2026-07-24-quick-access-commands-reply-keyboard-design.md`

---

## File Structure

- **Create** `app/handlers/quick_access.py` — билдеры (reply-клава, список команд), адаптер, роутинг-функции, `register_handlers`.
- **Create** `tests/handlers/test_quick_access.py` — юнит-тесты билдеров, helper'а активной подписки, роутинг-решения connect.
- **Modify** `app/bot.py` — регистрация `quick_access.register_handlers(dp)` + вызов `bot.set_my_commands(...)`.
- **Modify** `app/handlers/start.py` — установка reply-клавиатуры в начале `cmd_start`.

Тексты — через `texts.t(KEY, default)`; дефолты живут в коде (владелец может переопределить через `../ru-locales-live.json`). Правки `locales/ru.json` в этом плане НЕ требуются.

---

### Task 1: Reply-клавиатура (билдер)

**Files:**
- Create: `app/handlers/quick_access.py`
- Test: `tests/handlers/test_quick_access.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/handlers/test_quick_access.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_reply_keyboard_layout -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError` (модуля ещё нет).

- [ ] **Step 3: Write minimal implementation**

```python
# app/handlers/quick_access.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_reply_keyboard_layout -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/handlers/quick_access.py tests/handlers/test_quick_access.py
git commit -m "feat: reply-клавиатура быстрого доступа (билдер)"
```

---

### Task 2: Список команд для set_my_commands

**Files:**
- Modify: `app/handlers/quick_access.py`
- Test: `tests/handlers/test_quick_access.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_bot_commands_order_and_labels -v`
Expected: FAIL with `ImportError: cannot import name 'get_bot_commands'`.

- [ ] **Step 3: Write minimal implementation**

Добавить в `app/handlers/quick_access.py` (импорт вверху `from aiogram.types import BotCommand, KeyboardButton, ReplyKeyboardMarkup`):

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_bot_commands_order_and_labels -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/handlers/quick_access.py tests/handlers/test_quick_access.py
git commit -m "feat: список bot-команд для меню /"
```

---

### Task 3: Helper активной подписки

**Files:**
- Modify: `app/handlers/quick_access.py`
- Test: `tests/handlers/test_quick_access.py`

- [ ] **Step 1: Write the failing test**

```python
from types import SimpleNamespace


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_has_active_subscription -v`
Expected: FAIL with `ImportError: cannot import name '_has_active_subscription'`.

- [ ] **Step 3: Write minimal implementation**

Добавить в `app/handlers/quick_access.py` (зеркалит логику `menu.py:198-199`):

```python
def _has_active_subscription(db_user) -> bool:
    subs = getattr(db_user, 'subscriptions', None) or []
    return any(
        getattr(s, 'is_active', False) or getattr(s, 'actual_status', None) == 'limited'
        for s in subs
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_has_active_subscription -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/handlers/quick_access.py tests/handlers/test_quick_access.py
git commit -m "feat: helper проверки активной подписки для quick access"
```

---

### Task 4: Адаптер message→callback и открытие экранов

**Files:**
- Modify: `app/handlers/quick_access.py`
- Test: `tests/handlers/test_quick_access.py`

Адаптер позволяет вызвать существующий callback-хендлер экрана из message-входа.
Рендеры экранов редактируют `callback.message`, поэтому подставляем свежее
сообщение бота: логотип-фото в logo-режиме (тогда работает `edit_media`/`edit_caption`),
иначе текст (тогда работает `edit_text`).

**Prerequisite (один раз):** тесты этой и следующих задач асинхронные. Если
`pytest-asyncio` не установлен в 3.13 (см. память про окружение) — поставить:
`py -3.13 -m pip install pytest-asyncio`. Тесты используют `@pytest.mark.asyncio`.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock


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

    source.answer.assert_awaited_once()  # отправлен текстовый placeholder
    handler.assert_awaited_once()
    adapter = handler.await_args.args[0]
    assert adapter.message is placeholder
    assert adapter.bot is bot
    # kwargs проброшены в хендлер экрана
    assert handler.await_args.kwargs == {'db_user': 'U', 'db': 'DB'}
    # adapter.answer() — awaitable no-op
    await adapter.answer()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_open_via_adapter_text_mode -v`
Expected: FAIL with `AttributeError: module ... has no attribute '_open_via_adapter'`.

- [ ] **Step 3: Write minimal implementation**

Добавить в `app/handlers/quick_access.py`:

```python
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

    async def answer(self, *args, **kwargs):  # noqa: D401 - no-op (алерты не нужны)
        return None


async def _open_via_adapter(source_message, bot, handler, **kwargs) -> None:
    from app.utils.message_patch import LOGO_PATH, get_logo_media

    if settings.ENABLE_LOGO_MODE and LOGO_PATH.exists():
        placeholder = await source_message.answer_photo(get_logo_media(), caption='…')
    else:
        placeholder = await source_message.answer('…')

    adapter = _MessageAsCallback(placeholder, source_message.from_user, bot)
    await handler(adapter, **kwargs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_open_via_adapter_text_mode -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/handlers/quick_access.py tests/handlers/test_quick_access.py
git commit -m "feat: адаптер message→callback для открытия экранов"
```

---

### Task 5: Роутинг-функции экранов (connect/pay/referrals/info/support/promo/docs)

**Files:**
- Modify: `app/handlers/quick_access.py`
- Test: `tests/handlers/test_quick_access.py`

Тонкие функции, которые командные и reply-хендлеры переиспользуют (DRY). Импорты
целевых хендлеров — локальные (внутри функций), чтобы избежать циклов импорта.

- [ ] **Step 1: Write the failing test**

```python
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

    # без подписки → на экран покупки
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py -k connect_routes -v`
Expected: FAIL with `AttributeError: ... '_route_connect'`.

- [ ] **Step 3: Write minimal implementation**

Добавить в `app/handlers/quick_access.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py -k connect_routes -v`
Expected: PASS (оба теста)

- [ ] **Step 5: Commit**

```bash
git add app/handlers/quick_access.py tests/handlers/test_quick_access.py
git commit -m "feat: роутинг-функции экранов quick access"
```

---

### Task 6: Хендлеры и register_handlers

**Files:**
- Modify: `app/handlers/quick_access.py`
- Test: `tests/handlers/test_quick_access.py`

Командные и reply-хендлеры вызывают общие `_route_*`. Reply-хендлеры регистрируются
с `StateFilter(None)`, чтобы не перехватывать ввод в FSM (тикеты, промокод и т.п.).
Тексты reply-кнопок для матчинга берутся из того же `_reply_button_texts`, что и
клавиатура — они не разъезжаются.

- [ ] **Step 1: Write the failing test**

```python
def test_register_handlers_wires_commands_and_reply_buttons():
    from unittest.mock import MagicMock

    from app.handlers import quick_access

    dp = MagicMock()
    dp.message = MagicMock()
    dp.message.register = MagicMock()

    quick_access.register_handlers(dp)

    # 5 команд (без /start — он в start.py) + 5 reply-кнопок = 10 регистраций
    assert dp.message.register.call_count == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_register_handlers_wires_commands_and_reply_buttons -v`
Expected: FAIL with `AttributeError: ... 'register_handlers'`.

- [ ] **Step 3: Write minimal implementation**

Добавить в `app/handlers/quick_access.py` (импорты вверху дополнить):

```python
from aiogram import Dispatcher, F
from aiogram.filters import Command, StateFilter
```

и:

```python
# --- Command handlers (сигнатуры: aiogram инжектит db_user/db/state/bot) ---

async def cmd_connect(message, db_user, db, state, bot):
    await _route_connect(message, bot=bot, db_user=db_user, db=db, state=state)


async def cmd_pay(message, db_user, db, state, bot):
    await _route_pay(message, bot=bot, db_user=db_user, db=db, state=state)


async def cmd_referrals(message, db_user, db, bot):
    await _route_referrals(message, bot=bot, db_user=db_user, db=db)


async def cmd_info(message, db_user, db, bot):
    await _route_info(message, bot=bot, db_user=db_user, db=db)


async def cmd_promo(message, db_user, state):
    await _route_promo(message, db_user=db_user, state=state)


# --- Reply-button handlers ---

async def rk_connect(message, db_user, db, state, bot):
    await _route_connect(message, bot=bot, db_user=db_user, db=db, state=state)


async def rk_promo(message, db_user, state):
    await _route_promo(message, db_user=db_user, state=state)


async def rk_support(message, db_user, bot):
    await _route_support(message, bot=bot, db_user=db_user)


async def rk_privacy(message, db_user, db, bot):
    await _route_doc(
        message, bot=bot, db_user=db_user, db=db,
        url=settings.PRIVACY_POLICY_URL, label_key='INFO_MENU_PRIVACY',
        label_default='Политика конфиденциальности',
    )


async def rk_agreement(message, db_user, db, bot):
    await _route_doc(
        message, bot=bot, db_user=db_user, db=db,
        url=settings.USER_AGREEMENT_URL, label_key='INFO_MENU_AGREEMENT',
        label_default='Пользовательское соглашение',
    )


def register_handlers(dp: Dispatcher) -> None:
    # Команды (/start регистрируется в start.py — здесь не дублируем)
    dp.message.register(cmd_connect, Command('connect'))
    dp.message.register(cmd_pay, Command('pay'))
    dp.message.register(cmd_referrals, Command('referrals'))
    dp.message.register(cmd_promo, Command('promo'))
    dp.message.register(cmd_info, Command('info'))

    # Reply-кнопки — матчинг по тексту, только вне FSM-состояний
    t = _reply_button_texts(get_texts(settings.DEFAULT_LANGUAGE))
    dp.message.register(rk_connect, F.text == t['connect'], StateFilter(None))
    dp.message.register(rk_promo, F.text == t['promo'], StateFilter(None))
    dp.message.register(rk_privacy, F.text == t['privacy'], StateFilter(None))
    dp.message.register(rk_agreement, F.text == t['agreement'], StateFilter(None))
    dp.message.register(rk_support, F.text == t['support'], StateFilter(None))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py::test_register_handlers_wires_commands_and_reply_buttons -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/handlers/quick_access.py tests/handlers/test_quick_access.py
git commit -m "feat: хендлеры команд и reply-кнопок quick access"
```

---

### Task 7: Регистрация модуля и set_my_commands в bot.py

**Files:**
- Modify: `app/bot.py` (импорт-блок хендлеров; регистрация ~строка 179; вызов перед `return bot, dp` ~строка 300)

- [ ] **Step 1: Добавить импорт модуля**

В `app/bot.py`, рядом с прочими импортами хендлеров (там, где `from app.handlers import start, menu, ...`), добавить `quick_access`:

```python
from app.handlers import quick_access
```

(Если хендлеры импортируются по одному — добавить строку `from app.handlers import quick_access` в тот же блок.)

- [ ] **Step 2: Зарегистрировать хендлеры**

В `app/bot.py` сразу после `start.register_handlers(dp)` (строка 179) добавить:

```python
    quick_access.register_handlers(dp)
```

Размещение раньше `menu`/`subscription` гарантирует, что reply-кнопки (строгий матч
по тексту + `StateFilter(None)`) не будут перехвачены общими текстовыми хендлерами.

- [ ] **Step 3: Вызвать set_my_commands при старте**

В `app/bot.py`, перед `logger.info('Бот успешно настроен')` / `return bot, dp` (~строка 300) добавить:

```python
    try:
        await bot.set_my_commands(quick_access.get_bot_commands(settings.DEFAULT_LANGUAGE))
        logger.info('📋 Меню команд установлено')
    except Exception as e:
        logger.warning('Не удалось установить меню команд', error=e)
```

- [ ] **Step 4: Проверить импорт/сборку**

Run: `py -3.13 -c "import app.bot"`
Expected: без ошибок импорта (модуль импортируется).

- [ ] **Step 5: Commit**

```bash
git add app/bot.py
git commit -m "feat: подключить quick access и set_my_commands в bot.py"
```

---

### Task 8: Установка reply-клавиатуры на /start

**Files:**
- Modify: `app/handlers/start.py` (`cmd_start`, начало функции ~строка 733)

Клавиатура ставится один раз в начале `cmd_start`, чтобы сработать на любом
пути (обычный старт, deep-link и т.п.). Язык — из `db_user`, иначе дефолтный.

Примечание: для совсем нового пользователя подсказка появится до welcome-экрана —
это осознанный компромисс (клавиатура «всегда под рукой»); большинство нажимают
/start уже зарегистрированными.

- [ ] **Step 1: Добавить импорты в start.py**

Убедиться, что в `app/handlers/start.py` есть (добавить, если нет):

```python
from app.config import settings
from app.handlers.quick_access import get_quick_reply_keyboard
from app.localization.texts import get_texts
```

(`settings`, `get_texts` в start.py почти наверняка уже импортированы — не дублировать.)

- [ ] **Step 2: Вставить установку клавиатуры в начале cmd_start**

Сразу после строки `data = await state.get_data() or {}` (строка 734) вставить:

```python
    # FreekVPN: ставим постоянную нижнюю клавиатуру быстрого доступа.
    # Отдельным сообщением, т.к. reply- и inline-разметку нельзя совместить в одном.
    _rk_lang = db_user.language if db_user else settings.DEFAULT_LANGUAGE
    try:
        await message.answer(
            get_texts(_rk_lang).t('RK_INSTALL_HINT', 'Меню всегда под рукой 👇'),
            reply_markup=get_quick_reply_keyboard(_rk_lang),
        )
    except Exception as e:
        logger.warning('Не удалось отправить reply-клавиатуру', error=e)
```

- [ ] **Step 3: Проверить импорт/сборку**

Run: `py -3.13 -c "import app.handlers.start"`
Expected: без ошибок (в частности, без циклического импорта quick_access ↔ start).

Если возникнет цикл импорта — заменить top-level импорт на локальный внутри
`cmd_start`: `from app.handlers.quick_access import get_quick_reply_keyboard`.

- [ ] **Step 4: Commit**

```bash
git add app/handlers/start.py
git commit -m "feat: установка reply-клавиатуры быстрого доступа на /start"
```

---

### Task 9: Полный прогон тестов и проверка

**Files:** —

- [ ] **Step 1: Прогнать новые тесты модуля**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py -v`
Expected: все PASS.

- [ ] **Step 2: Прогнать смежные тесты (регрессия start/menu/support)**

Run: `py -3.13 -m pytest tests/handlers/test_info_help_screen.py -v`
Expected: PASS (4 теста). Прочие async-тесты могут падать на сборе из-за
отсутствия `pytest-asyncio` в 3.13 — это преэкзистинг, не регрессия (см. память).
Для async-тестов этого плана `pytest-asyncio` требуется: если не установлен —
`py -3.13 -m pip install pytest-asyncio` и повторить Step 1.

- [ ] **Step 3: Ручная проверка на тестовом боте (docker-стек)**

Запустить локальный стек и в тестовом боте проверить:
- `/start` → появилась нижняя клавиатура из 3 рядов (2/2/1).
- Кнопка «/» показывает 6 команд в нужном порядке.
- Reply: «Как подключиться?» с активной подпиской → гайд; без подписки → «Оплатить».
- Reply: «Ввести промокод» → запрос кода, ввод кода активирует (совместимо с `process_promocode`).
- Reply: «Политика»/«Соглашение» → сообщение со ссылкой-кнопкой на telegra.ph.
- Reply: «Поддержка» → экран поддержки.
- Команды `/connect`, `/pay`, `/referrals`, `/promo`, `/info` открывают те же экраны.
- Ввод в тикет НЕ перехватывается reply-кнопками (StateFilter(None)).

- [ ] **Step 4: Финальный commit (если были правки по итогам проверки)**

```bash
git add -A
git commit -m "test: quick access — прогон и правки по итогам проверки"
```

---

## Деплой (владельца)

- Только код → `git pull` + `docker compose up -d --build` на сервере
  (`193.23.199.99`, `/opt/remnawave-bedolaga-telegram-bot`).
- Новых `.env` не требуется — используются `SUPPORT_USERNAME`, `PRIVACY_POLICY_URL`,
  `USER_AGREEMENT_URL` (уже заведены).
- Тексты команд/кнопок можно переопределить ключами `CMD_*`/`RK_*` в
  `../ru-locales-live.json` + scp (необязательно; дефолты в коде).

## Заметки по рискам

- **Циклы импорта:** `quick_access` импортирует из `menu`/`purchase`/`referral`/`support`
  локально (внутри функций) — цикла быть не должно. `start` → `quick_access` (top-level):
  если всплывёт цикл, перенести импорт в локальный (Task 8, Step 3).
- **Матчинг reply-кнопок:** и клавиатура, и хендлеры читают подписи из
  `_reply_button_texts(get_texts('ru'))` → синхронны. При переопределении текстов в
  live-локали бот перечитывает их при старте (rebuild), совпадение сохраняется.
- **Тип placeholder:** в logo-режиме — фото (editable через edit_media/edit_caption),
  иначе текст (edit_text). Оба совместимы с существующими рендерами экранов.
