# Кнопка «Получить триал» в главном меню — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Показывать в главном меню синюю кнопку «🎁 Получить N дней» (и подсказку в статус-карточке), когда триал ещё доступен, чтобы юзер, пропустивший кнопку под приветствием, мог активировать триал из меню.

**Architecture:** Гейт доступности считается ВНУТРИ билдеров из объекта `user` (без проводки через call-sites): хелпер `is_trial_available_for_user(user)` в `inline.py`. Клавиатура добавляет кнопку (`get_main_menu_keyboard`, гейт вычисляет async-обёртка из `user=`), карточка (`_build_main_menu_status_card`) заменяет блок «Подписка не активна» на приглашение. Кнопка ведёт на существующий `trial_activate` — новой логики активации нет.

**Tech Stack:** Python 3.13, aiogram 3, pytest (`py -3.13 -m pytest`).

**Spec:** `docs/superpowers/specs/2026-07-24-menu-trial-button-design.md`

---

## File Structure

- **Modify** `app/keyboards/inline.py` — хелпер `is_trial_available_for_user`; параметр `trial_available` + синяя кнопка в `get_main_menu_keyboard`; вычисление гейта в `get_main_menu_keyboard_async` (fallback-ветка).
- **Modify** `app/handlers/menu.py` — в `_build_main_menu_status_card` подсказка про триал вместо «Подписка не активна».
- **Create** `tests/handlers/test_menu_trial_button.py` — тесты хелпера, кнопки, карточки.

Тексты — `texts.t(KEY, default)`, дефолты в коде. `{days}` = `settings.TRIAL_DURATION_DAYS`.

**Заметка про pydantic settings в тестах:** `settings` — инстанс pydantic-модели. МЕТОДЫ (`is_trial_disabled_for_user`, `is_cabinet_mode`) патчить на КЛАССЕ: `monkeypatch.setattr(type(settings), 'name', lambda self, ...: ...)`. ПОЛЯ (`TRIAL_DURATION_DAYS`) — на инстансе: `monkeypatch.setattr(settings, 'TRIAL_DURATION_DAYS', N)`. Патч метода на инстансе кидает `ValueError` (no field).

---

### Task 1: Хелпер `is_trial_available_for_user`

**Files:**
- Modify: `app/keyboards/inline.py`
- Test: `tests/handlers/test_menu_trial_button.py`

- [ ] **Step 1: Написать падающий тест**

```python
# tests/handlers/test_menu_trial_button.py
import pytest

from app.config import settings
from app.keyboards.inline import is_trial_available_for_user


class _FakeUser:
    def __init__(self, auth_type='telegram', used=False):
        self.auth_type = auth_type
        self._used = used

    def is_trial_already_used(self):
        return self._used


def test_trial_available_when_eligible(monkeypatch):
    monkeypatch.setattr(settings, 'TRIAL_DURATION_DAYS', 14)
    monkeypatch.setattr(type(settings), 'is_trial_disabled_for_user', lambda self, at: False)
    assert is_trial_available_for_user(_FakeUser(used=False)) is True


def test_trial_unavailable_when_used(monkeypatch):
    monkeypatch.setattr(settings, 'TRIAL_DURATION_DAYS', 14)
    monkeypatch.setattr(type(settings), 'is_trial_disabled_for_user', lambda self, at: False)
    assert is_trial_available_for_user(_FakeUser(used=True)) is False


def test_trial_unavailable_when_duration_zero(monkeypatch):
    monkeypatch.setattr(settings, 'TRIAL_DURATION_DAYS', 0)
    monkeypatch.setattr(type(settings), 'is_trial_disabled_for_user', lambda self, at: False)
    assert is_trial_available_for_user(_FakeUser(used=False)) is False


def test_trial_unavailable_when_disabled_for_type(monkeypatch):
    monkeypatch.setattr(settings, 'TRIAL_DURATION_DAYS', 14)
    monkeypatch.setattr(type(settings), 'is_trial_disabled_for_user', lambda self, at: True)
    assert is_trial_available_for_user(_FakeUser(used=False)) is False


def test_trial_unavailable_when_user_none():
    assert is_trial_available_for_user(None) is False
```

- [ ] **Step 2: Прогнать — падает**

Run: `py -3.13 -m pytest tests/handlers/test_menu_trial_button.py -k trial -v`
Expected: FAIL (ImportError: cannot import name 'is_trial_available_for_user').

- [ ] **Step 3: Реализовать** — добавить в `app/keyboards/inline.py` (рядом с `get_main_menu_keyboard`; `settings` уже импортирован в модуле):

```python
def is_trial_available_for_user(user) -> bool:
    """Гейт показа кнопки/подсказки триала в меню — те же условия, что проверяет
    activate_trial перед выдачей. True, если триал юзеру ещё положен.
    Требует загруженного user.subscriptions (для is_trial_already_used)."""
    if user is None:
        return False
    if settings.TRIAL_DURATION_DAYS <= 0:
        return False
    if settings.is_trial_disabled_for_user(getattr(user, 'auth_type', 'telegram')):
        return False
    try:
        return not user.is_trial_already_used()
    except Exception:
        return False
```

- [ ] **Step 4: Прогнать — проходит**

Run: `py -3.13 -m pytest tests/handlers/test_menu_trial_button.py -k trial -v`
Expected: PASS (5 тестов).

- [ ] **Step 5: Commit**

```bash
git add app/keyboards/inline.py tests/handlers/test_menu_trial_button.py
git commit -m "feat: хелпер is_trial_available_for_user"
```

---

### Task 2: Синяя кнопка триала в главном меню

**Files:**
- Modify: `app/keyboards/inline.py` (`get_main_menu_keyboard` ~571-649, `get_main_menu_keyboard_async` fallback ~143-155)
- Test: `tests/handlers/test_menu_trial_button.py`

- [ ] **Step 1: Написать падающий тест** (APPEND)

```python
from app.keyboards.inline import get_main_menu_keyboard


def _trial_button(kb):
    for row in kb.inline_keyboard:
        for btn in row:
            if btn.callback_data == 'trial_activate':
                return btn
    return None


def test_menu_has_blue_trial_button_when_available(monkeypatch):
    monkeypatch.setattr(type(settings), 'is_cabinet_mode', lambda self: False)
    monkeypatch.setattr(settings, 'TRIAL_DURATION_DAYS', 14)
    kb = get_main_menu_keyboard(language='ru', trial_available=True)
    btn = _trial_button(kb)
    assert btn is not None
    assert getattr(btn, 'style', None) == 'primary'
    # кнопка триала — выше «Оплатить»
    flat = [b for row in kb.inline_keyboard for b in row]
    idx_trial = next(i for i, b in enumerate(flat) if b.callback_data == 'trial_activate')
    idx_pay = next(i for i, b in enumerate(flat) if b.callback_data == 'menu_buy')
    assert idx_trial < idx_pay


def test_menu_no_trial_button_when_unavailable(monkeypatch):
    monkeypatch.setattr(type(settings), 'is_cabinet_mode', lambda self: False)
    kb = get_main_menu_keyboard(language='ru', trial_available=False)
    assert _trial_button(kb) is None
```

- [ ] **Step 2: Прогнать — падает**

Run: `py -3.13 -m pytest tests/handlers/test_menu_trial_button.py -k trial_button -v`
Expected: FAIL (`get_main_menu_keyboard() got an unexpected keyword argument 'trial_available'`).

- [ ] **Step 3: Реализовать**

3a. В сигнатуру `get_main_menu_keyboard` (`app/keyboards/inline.py:571`) добавить параметр. Текущая сигнатура заканчивается так:
```python
    *,
    is_moderator: bool = False,
    custom_buttons: list[InlineKeyboardButton] | None = None,
) -> InlineKeyboardMarkup:
```
Заменить на:
```python
    *,
    is_moderator: bool = False,
    custom_buttons: list[InlineKeyboardButton] | None = None,
    trial_available: bool = False,
) -> InlineKeyboardMarkup:
```

3b. В теле, сразу после `keyboard: list[list[InlineKeyboardButton]] = []` (строка ~611, перед комментарием «Ряд 1: Оплатить») вставить:
```python
    # Синяя кнопка активации триала — только если триал ещё доступен. Ведёт на тот
    # же trial_activate, что и кнопка под приветствием (юзер мог её пропустить).
    if trial_available:
        keyboard.append([
            InlineKeyboardButton(
                text=texts.t('MENU_MAIN_GET_TRIAL', '🎁 Получить {days} дней').format(
                    days=settings.TRIAL_DURATION_DAYS
                ),
                callback_data='trial_activate',
                style='primary',
            )
        ])
```

3c. В `get_main_menu_keyboard_async` (`app/keyboards/inline.py:143`) в fallback-вызов `get_main_menu_keyboard(...)` добавить последним аргументом `trial_available`:
```python
    # Fallback на синхронную версию
    return get_main_menu_keyboard(
        language=language,
        is_admin=is_admin,
        has_had_paid_subscription=has_had_paid_subscription,
        has_active_subscription=has_active_subscription,
        subscription_is_active=subscription_is_active,
        balance_kopeks=balance_kopeks,
        subscription=subscription,
        show_resume_checkout=show_resume_checkout,
        has_saved_cart=has_saved_cart,
        is_moderator=is_moderator,
        custom_buttons=custom_buttons,
        trial_available=is_trial_available_for_user(user),
    )
```
(`user` — уже параметр async-обёртки; `is_trial_available_for_user` определён в этом же модуле. MENU_LAYOUT-ветка не трогается — в classic-режиме FreekVPN используется fallback.)

- [ ] **Step 4: Прогнать — проходит**

Run: `py -3.13 -m pytest tests/handlers/test_menu_trial_button.py -k trial_button -v`
Expected: PASS. Также весь файл: `py -3.13 -m pytest tests/handlers/test_menu_trial_button.py -v`.

- [ ] **Step 5: Проверить импорт**

Run: `py -3.13 -c "import app.keyboards.inline; import app.bot"`
Expected: без ошибок.

- [ ] **Step 6: Commit**

```bash
git add app/keyboards/inline.py tests/handlers/test_menu_trial_button.py
git commit -m "feat: синяя кнопка Получить триал в главном меню"
```

---

### Task 3: Подсказка про триал в статус-карточке

**Files:**
- Modify: `app/handlers/menu.py` (`_build_main_menu_status_card` ~1396-1470)
- Test: `tests/handlers/test_menu_trial_button.py`

- [ ] **Step 1: Написать падающий тест** (APPEND)

```python
@pytest.mark.asyncio
async def test_status_card_shows_trial_invite_when_available(monkeypatch):
    from app.handlers.menu import _build_main_menu_status_card
    from app.localization.texts import get_texts

    monkeypatch.setattr(settings, 'TRIAL_DURATION_DAYS', 14)
    monkeypatch.setattr(type(settings), 'is_trial_disabled_for_user', lambda self, at: False)
    monkeypatch.setattr(type(settings), 'is_referral_program_enabled', lambda self: False)

    class _User:
        subscription = None
        subscriptions = []
        auth_type = 'telegram'

        def is_trial_already_used(self):
            return False

    text = await _build_main_menu_status_card(_User(), get_texts('ru'), db=None)
    assert '14' in text
    assert 'Подписка не активна' not in text


@pytest.mark.asyncio
async def test_status_card_shows_none_when_trial_used(monkeypatch):
    from app.handlers.menu import _build_main_menu_status_card
    from app.localization.texts import get_texts

    monkeypatch.setattr(settings, 'TRIAL_DURATION_DAYS', 14)
    monkeypatch.setattr(type(settings), 'is_trial_disabled_for_user', lambda self, at: False)
    monkeypatch.setattr(type(settings), 'is_referral_program_enabled', lambda self: False)

    class _User:
        subscription = None
        subscriptions = [object()]  # есть подписка → триал использован
        auth_type = 'telegram'

        def is_trial_already_used(self):
            return True

    text = await _build_main_menu_status_card(_User(), get_texts('ru'), db=None)
    assert 'Подписка не активна' in text
```

- [ ] **Step 2: Прогнать — падает**

Run: `py -3.13 -m pytest tests/handlers/test_menu_trial_button.py -k status_card -v`
Expected: FAIL (первый тест: сейчас всегда «Подписка не активна», строки про 14 нет).

- [ ] **Step 3: Реализовать** — в `app/handlers/menu.py`, функция `_build_main_menu_status_card`.

3a. В начале функции (после строки `subscription = getattr(user, 'subscription', None)`, ~1407) добавить вычисление гейта (локальный импорт — избегаем цикла):
```python
    from app.keyboards.inline import is_trial_available_for_user

    trial_available = subscription is None and is_trial_available_for_user(user)
```

3b. Заменить блок добавления статов (строки ~1462-1470):
```python
    # Статы в blockquote (как выделенный блок в профиле)
    lines.append(
        texts.t(
            'MAIN_MENU_STATS_BLOCK',
            '<blockquote><b>Осталось:</b> {remaining}\n'
            '<b>Устройства:</b> {devices}\n'
            '<b>Трафик:</b> {traffic}</blockquote>',
        ).format(remaining=remaining, devices=devices_text, traffic=traffic)
    )
```
на:
```python
    if trial_available:
        # Триал ещё доступен (юзер мог пропустить кнопку под приветствием) —
        # приглашаем забрать его кнопкой ниже вместо «Подписка не активна».
        lines.append(
            texts.t(
                'MAIN_MENU_TRIAL_INVITE',
                '<blockquote>🎁 Тебе доступно {days} дней бесплатно — забери кнопкой ниже.</blockquote>',
            ).format(days=settings.TRIAL_DURATION_DAYS)
        )
    else:
        # Статы в blockquote (как выделенный блок в профиле)
        lines.append(
            texts.t(
                'MAIN_MENU_STATS_BLOCK',
                '<blockquote><b>Осталось:</b> {remaining}\n'
                '<b>Устройства:</b> {devices}\n'
                '<b>Трафик:</b> {traffic}</blockquote>',
            ).format(remaining=remaining, devices=devices_text, traffic=traffic)
        )
```

- [ ] **Step 4: Прогнать — проходит**

Run: `py -3.13 -m pytest tests/handlers/test_menu_trial_button.py -k status_card -v`
Expected: PASS (оба).

- [ ] **Step 5: Проверить импорт**

Run: `py -3.13 -c "import app.handlers.menu; import app.bot"`
Expected: без ошибок (в частности, без цикла inline↔menu — импорт хелпера локальный внутри функции).

- [ ] **Step 6: Commit**

```bash
git add app/handlers/menu.py tests/handlers/test_menu_trial_button.py
git commit -m "feat: подсказка про триал в статус-карточке главного меню"
```

---

### Task 4: Полный прогон и проверка

- [ ] **Step 1: Весь новый файл тестов**

Run: `py -3.13 -m pytest tests/handlers/test_menu_trial_button.py -v`
Expected: все PASS (5 + 2 + 2 = 9).

- [ ] **Step 2: Смежные тесты (регрессия меню/quick access)**

Run: `py -3.13 -m pytest tests/handlers/test_quick_access.py tests/ -k "menu or start" -v`
Expected: PASS (преэкзистинг-падения async-сбора, не связанные с этим изменением — ок, отметить).

- [ ] **Step 3: Ручная проверка (локальный docker-стек, тестовый бот)**

Пересобрать (`docker compose -f docker-compose.local.yml up -d --build bot`) и на СВЕЖЕМ юзере без подписки:
- `/start` → в меню синяя «🎁 Получить 14 дней» над зелёной «Оплатить»; карточка пишет «🎁 Тебе доступно 14 дней бесплатно…».
- Нажать «Получить 14 дней» → активируется триал (тот же экран, что кнопка под приветствием).
- После активации `/start` → кнопки триала нет, «Оплатить» на месте, карточка показывает дни/устройства/трафик.
- ⚠️ Локально меню тормозит ~30с (панель недоступна) — норм, не связано.

- [ ] **Step 4: Финальный commit (если были правки по итогам)**

```bash
git add -A && git commit -m "test: кнопка триала — прогон и правки"
```

---

## Деплой (владельца)

- Только код → `git pull` + `docker compose up -d --build`. Новых `.env` не требуется.
- Тексты можно переопределить ключами `MENU_MAIN_GET_TRIAL` / `MAIN_MENU_TRIAL_INVITE`
  в `../ru-locales-live.json` (необязательно; дефолты в коде).

## Заметки по рискам

- **Цикл импорта:** `is_trial_available_for_user` живёт в `inline.py` (импортирует только
  `settings`), `menu.py` берёт его ЛОКАЛЬНЫМ импортом внутри `_build_main_menu_status_card`
  → цикла нет (inline не импортирует menu).
- **MENU_LAYOUT_ENABLED=True:** кнопка триала добавляется только в classic-fallback. В
  конфиг-меню (не используется на FreekVPN) кнопки не будет — вне scope.
- **`style='primary'`:** поддерживается Bot API этого бота (используется в inline.py уже
  4×). Синий цвет, контраст с зелёной «Оплатить».
