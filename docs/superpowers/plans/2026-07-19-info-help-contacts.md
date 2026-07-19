# Инфо-экран «Помощь и контакты» — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Переработать инфо-экран классического бота в единый экран «Помощь и контакты» с быстрыми ссылками (текст + кнопки): поддержка → внешний бот `@FreakVPN_SupportBot`, Политика и Соглашение → telegra.ph, FAQ и тикеты убраны с экрана.

**Architecture:** Чистый билдер `build_help_contacts_screen` (новый модуль `app/utils/info_help_screen.py`) собирает caption + ряды кнопок из готовых значений (URL/контакт/тексты) — тестируется юнит-тестом без БД. Хендлер `show_info_menu` резолвит конфиг (`SUPPORT_USERNAME`, `PRIVACY_POLICY_URL`, `USER_AGREEMENT_URL`) и передаёт в билдер. Старые БД-хендлеры Политики/Оферты и тикет-подсистема остаются в коде, просто не вызываются с этого экрана.

**Tech Stack:** Python, aiogram 3, pytest. Спека: `docs/superpowers/specs/2026-07-19-info-help-contacts-design.md`.

---

### Task 1: Чистый билдер экрана «Помощь и контакты»

**Files:**
- Create: `app/utils/info_help_screen.py`
- Test: `tests/handlers/test_info_help_screen.py`

- [ ] **Step 1: Написать падающий тест**

Создать `tests/handlers/test_info_help_screen.py`:

```python
from app.localization.texts import get_texts
from app.utils.info_help_screen import build_help_contacts_screen


def _urls(rows):
    return [b.url for row in rows for b in row if b.url]


def _callbacks(rows):
    return [b.callback_data for row in rows for b in row if b.callback_data]


def _texts():
    return get_texts('ru')


def test_full_screen_has_all_links_and_buttons():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='https://t.me/FreakVPN_SupportBot',
        privacy_url='https://telegra.ph/privacy',
        agreement_url='https://telegra.ph/agreement',
    )

    assert 'Помощь и контакты' in caption
    assert '<blockquote>' in caption
    assert '@FreakVPN_SupportBot' in caption
    assert 'https://telegra.ph/privacy' in caption
    assert 'https://telegra.ph/agreement' in caption

    urls = _urls(rows)
    assert 'https://t.me/FreakVPN_SupportBot' in urls
    assert 'https://telegra.ph/privacy' in urls
    assert 'https://telegra.ph/agreement' in urls
    assert 'back_to_menu' in _callbacks(rows)


def test_support_hidden_when_no_url():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='',
        privacy_url='https://telegra.ph/privacy',
        agreement_url='https://telegra.ph/agreement',
    )
    assert '@FreakVPN_SupportBot' not in caption
    assert 'https://t.me/FreakVPN_SupportBot' not in _urls(rows)
    # Кабинет-строка остаётся
    assert 'Кабинет' in caption


def test_documents_hidden_when_no_url():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='https://t.me/FreakVPN_SupportBot',
        privacy_url='',
        agreement_url='',
    )
    assert 'telegra.ph' not in caption
    assert _urls(rows) == ['https://t.me/FreakVPN_SupportBot']
    assert 'back_to_menu' in _callbacks(rows)


def test_back_button_always_present():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='',
        support_url='',
        privacy_url='',
        agreement_url='',
    )
    assert 'back_to_menu' in _callbacks(rows)
    assert rows[-1][0].callback_data == 'back_to_menu'
```

- [ ] **Step 2: Запустить тест — убедиться, что падает**

Run: `python -m pytest tests/handlers/test_info_help_screen.py -v`
Expected: FAIL с `ModuleNotFoundError: No module named 'app.utils.info_help_screen'`

- [ ] **Step 3: Реализовать билдер**

Создать `app/utils/info_help_screen.py`:

```python
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
                text=texts.t('INFO_MENU_SUPPORT', '💬 Поддержка'),
                url=support_url,
            )
        ])
    if privacy_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('INFO_MENU_PRIVACY', '🔒 Политика конфиденциальности'),
                url=privacy_url,
            )
        ])
    if agreement_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('INFO_MENU_AGREEMENT', '📄 Пользовательское соглашение'),
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
```

- [ ] **Step 4: Запустить тест — убедиться, что проходит**

Run: `python -m pytest tests/handlers/test_info_help_screen.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Коммит**

```bash
git add app/utils/info_help_screen.py tests/handlers/test_info_help_screen.py
git commit -m "feat(info): билдер экрана Помощь и контакты + тесты"
```

---

### Task 2: Конфиг-переменные для telegra.ph-ссылок

**Files:**
- Modify: `app/config.py:927` (после `MAIN_MENU_SITE_URL`)
- Modify: `.env.example:946` (после `MAIN_MENU_SITE_URL=...`)

- [ ] **Step 1: Добавить переменные в config.py**

В `app/config.py` сразу после строки `MAIN_MENU_SITE_URL: str = 'https://cabinetipn.duckdns.org'` (строка 927) вставить:

```python
    # FreekVPN: внешние ссылки на юридические документы (telegra.ph, Instant View).
    # Пусто → соответствующий пункт скрыт в инфо-экране «Помощь и контакты».
    PRIVACY_POLICY_URL: str = ''
    USER_AGREEMENT_URL: str = ''
```

- [ ] **Step 2: Добавить в .env.example**

В `.env.example` после строки `MAIN_MENU_SITE_URL=https://cabinetipn.duckdns.org` (строка 946) вставить:

```
# Юридические документы (telegra.ph). Пусто → пункт скрыт в «Помощь и контакты».
PRIVACY_POLICY_URL=https://telegra.ph/Politika-konfidencialnosti-FreekVPN-07-19
USER_AGREEMENT_URL=https://telegra.ph/Polzovatelskoe-soglashenie-FreekVPN-07-19
```

- [ ] **Step 3: Проверить, что конфиг импортируется и значения читаются**

Run: `python -c "from app.config import settings; print(repr(settings.PRIVACY_POLICY_URL), repr(settings.USER_AGREEMENT_URL))"`
Expected: печатает два значения без ошибок (пустые строки, если `.env` без них, или значения из `.env`).

- [ ] **Step 4: Коммит**

```bash
git add app/config.py .env.example
git commit -m "feat(config): PRIVACY_POLICY_URL и USER_AGREEMENT_URL для telegra.ph"
```

---

### Task 3: Переключить show_info_menu на новый билдер

**Files:**
- Modify: `app/handlers/menu.py:457-547` (тело `show_info_menu`)
- Modify: `app/handlers/menu.py:39` область импортов (добавить импорт билдера)

- [ ] **Step 1: Добавить импорт билдера**

В `app/handlers/menu.py` рядом с `from app.utils.photo_message import edit_or_answer_photo` (строка 39) добавить:

```python
from app.utils.info_help_screen import build_help_contacts_screen
```

- [ ] **Step 2: Переписать тело show_info_menu**

Заменить весь блок от строки `texts = get_texts(db_user.language)` (внутри `show_info_menu`, ~строка 474) и до `await callback.answer()` включительно (~строка 547) на:

```python
    texts = get_texts(db_user.language)

    try:
        support_enabled = SupportSettingsService.is_support_menu_enabled()
    except Exception:
        support_enabled = settings.SUPPORT_MENU_ENABLED

    support_url = settings.get_support_contact_url() or ''
    if not support_enabled:
        support_url = ''

    caption, rows = build_help_contacts_screen(
        texts,
        support_username=settings.SUPPORT_USERNAME,
        support_url=support_url,
        privacy_url=(settings.PRIVACY_POLICY_URL or '').strip(),
        agreement_url=(settings.USER_AGREEMENT_URL or '').strip(),
    )

    await edit_or_answer_photo(
        callback=callback,
        caption=caption,
        keyboard=types.InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode='HTML',
    )
    await callback.answer()
```

Блок проверки `if db_user is None:` в начале функции (строки 462-472) НЕ трогать — оставить как есть.

- [ ] **Step 3: Проверить, что модуль импортируется**

Run: `python -c "import app.handlers.menu"`
Expected: без ошибок (ImportError/NameError).

- [ ] **Step 4: Прогнать существующий тест инфо-клавиатуры (регрессия)**

Run: `python -m pytest tests/handlers/test_info_menu_keyboard.py tests/handlers/test_info_help_screen.py -v`
Expected: PASS. (Первый тестирует легаси `get_info_menu_keyboard`, который мы не трогали, — должен остаться зелёным.)

- [ ] **Step 5: Коммит**

```bash
git add app/handlers/menu.py
git commit -m "feat(info): show_info_menu — экран Помощь и контакты (telegra.ph + внешняя поддержка)"
```

---

### Task 4: Дефолты локаль-ключей в ru.json

**Files:**
- Modify: `app/localization/locales/ru.json:1132` (рядом с `MENU_INFO_HEADER`)

- [ ] **Step 1: Добавить ключи в ru.json**

В `app/localization/locales/ru.json` сразу после строки `"MENU_INFO_HEADER": "ℹ️ <b>Инфо</b>",` (строка 1132) вставить:

```json
  "INFO_HELP_HEADER": "💡 <b>Помощь и контакты</b>",
  "INFO_HELP_INTRO": "Если что-то непонятно — здесь все быстрые ссылки.",
  "INFO_HELP_READ": "читать",
  "INFO_HELP_SUPPORT_LINE": "• Поддержка: <a href=\"{url}\">{username}</a>",
  "INFO_HELP_CABINET_LINE": "• Кабинет: подписка, баланс и установка — в главном меню",
  "INFO_HELP_PRIVACY_LINE": "• Политика конфиденциальности: <a href=\"{url}\">{read}</a>",
  "INFO_HELP_AGREEMENT_LINE": "• Пользовательское соглашение: <a href=\"{url}\">{read}</a>",
  "INFO_MENU_AGREEMENT": "📄 Пользовательское соглашение",
```

- [ ] **Step 2: Проверить валидность JSON**

Run: `python -c "import json; json.load(open('app/localization/locales/ru.json', encoding='utf-8')); print('ok')"`
Expected: печатает `ok` (JSON валиден, запятые на месте).

- [ ] **Step 3: Проверить, что ключи читаются локализацией**

Run: `python -c "from app.localization.texts import get_texts; t=get_texts('ru'); print(t.t('INFO_HELP_HEADER','')); print(t.t('INFO_MENU_AGREEMENT',''))"`
Expected: печатает `💡 <b>Помощь и контакты</b>` и `📄 Пользовательское соглашение`.

- [ ] **Step 4: Коммит**

```bash
git add app/localization/locales/ru.json
git commit -m "feat(i18n): дефолты ключей экрана Помощь и контакты"
```

---

### Task 5: Финальная проверка

- [ ] **Step 1: Прогнать релевантные тесты**

Run: `python -m pytest tests/handlers/test_info_help_screen.py tests/handlers/test_info_menu_keyboard.py tests/cabinet/test_info_display_mode_gating.py -v`
Expected: всё зелёное.

- [ ] **Step 2: Ручная сборка экрана с прод-значениями (дымовой тест)**

Run:
```bash
python -c "from app.localization.texts import get_texts; from app.utils.info_help_screen import build_help_contacts_screen; c,r=build_help_contacts_screen(get_texts('ru'), support_username='@FreakVPN_SupportBot', support_url='https://t.me/FreakVPN_SupportBot', privacy_url='https://telegra.ph/Politika-konfidencialnosti-FreekVPN-07-19', agreement_url='https://telegra.ph/Polzovatelskoe-soglashenie-FreekVPN-07-19'); print(c); print('---'); print([[b.text for b in row] for row in r])"
```
Expected: caption с заголовком, blockquote, строками Поддержка/Кабинет/Политика/Соглашение; список кнопок `[['💬 Поддержка'], ['🔒 Политика конфиденциальности'], ['📄 Пользовательское соглашение'], ['← Назад']]`.

- [ ] **Step 3: Убедиться, что рабочая копия чиста**

Run: `git status -s`
Expected: пусто (всё закоммичено; untracked `assets/`, `locales/` — не наши, игнорируем).

---

## Действия владельца перед деплоем (вне кода)

1. В реальный `.env` на сервере: `SUPPORT_USERNAME=@FreakVPN_SupportBot`, `PRIVACY_POLICY_URL=https://telegra.ph/Politika-konfidencialnosti-FreekVPN-07-19`, `USER_AGREEMENT_URL=https://telegra.ph/Polzovatelskoe-soglashenie-FreekVPN-07-19`.
2. Убедиться, что `SUPPORT_MENU_ENABLED=true` (дефолт).
3. Внести новые ключи `INFO_HELP_*` / `INFO_MENU_AGREEMENT` в мастер `../ru-locales-live.json` (если хочет переопределить дефолты) и залить на сервер поверх `locales/ru.json`.
4. git pull + docker compose build + up.
