# FreekVPN Connect / Support / Promo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Переверстать экран подключения (Happ + INCY, две one-tap кнопки), экран поддержки (3 канала), и вернуть кнопку промокода в оплату — по образцу веб-кабинета.

**Architecture:** Экраны собираются чистыми билдер-функциями в `app/utils/` (как существующий `info_help_screen.py`) — их легко юнит-тестировать; хендлеры только резолвят настройки и рендерят. Deep-link `incy://` работает через новый https-редирект `/incy` (зеркало `/happ`). Промокод-логика уже есть — добавляется только точка входа.

**Tech Stack:** Python 3.13, aiogram 3.x, FastAPI (unified webserver), pydantic-settings, pytest.

**Тесты гонять:** `py -3.13 -m pytest <path> -v` (системный python 3.10 не тянет `conftest.py`). Все тесты в плане синхронные (pytest-asyncio не нужен).

---

## File Structure

- **Create** `app/utils/connect_screen.py` — билдер экрана подключения.
- **Create** `app/utils/support_screen.py` — билдер карточки поддержки.
- **Create** `tests/utils/test_connect_screen.py`, `tests/utils/test_support_screen.py`, `tests/utils/test_incy_scheme.py`, `tests/utils/test_promocode_button.py`.
- **Modify** `app/config.py` — 3 настройки + геттеры.
- **Modify** `app/utils/subscription_utils.py` — INCY-конвертер + redirect-хелпер (+ DRY-рефактор happ-хелпера).
- **Modify** `app/webserver/unified_app.py` — обобщить рендер редиректа, добавить роут `/incy`.
- **Modify** `app/handlers/subscription/purchase.py` — `show_install_guide_devices` через билдер.
- **Modify** `app/handlers/support.py` — `show_support_info` через билдер.
- **Modify** `app/utils/info_help_screen.py` — кнопка «Поддержка» → callback `menu_support`.
- **Modify** `tests/handlers/test_info_help_screen.py` — под новый callback.
- **Modify** `app/handlers/subscription/tariff_purchase.py` — кнопка промокода в двух клавиатурах.
- **Modify** `.env.example` — новые настройки.

---

## Task 1: Config settings

**Files:**
- Modify: `app/config.py` (поля рядом с `SUPPORT_USERNAME:37` и `HAPP_DOWNLOAD_LINK_*:956`; геттеры рядом с `get_happ_cryptolink_redirect_template:2829` и `get_support_email` рядом с `get_support_contact_url:3242`)
- Modify: `.env.example`

- [ ] **Step 1: Add settings fields**

Рядом с `SUPPORT_USERNAME: str = '@support'` (строка ~37) добавить:

```python
    SUPPORT_EMAIL: str = ''
```

Рядом с блоком `HAPP_DOWNLOAD_LINK_*` (строки ~956-960) добавить:

```python
    INCY_DOWNLOAD_LINK: str = 'https://apps.apple.com/app/id6756943388'
    INCY_CRYPTOLINK_REDIRECT_TEMPLATE: str | None = None
```

- [ ] **Step 2: Add getters**

После `get_happ_cryptolink_redirect_template` (строка ~2831) добавить:

```python
    def get_incy_download_link(self) -> str | None:
        link = (self.INCY_DOWNLOAD_LINK or '').strip()
        return link or None

    def get_incy_cryptolink_redirect_template(self) -> str | None:
        template = (self.INCY_CRYPTOLINK_REDIRECT_TEMPLATE or '').strip()
        return template or None
```

После `get_support_contact_display_html` (строка ~3295) добавить:

```python
    def get_support_email(self) -> str:
        return (self.SUPPORT_EMAIL or '').strip()
```

- [ ] **Step 3: Add to .env.example**

Добавить в `.env.example` (рядом с секцией HAPP / SUPPORT):

```dotenv
# Экран подключения — INCY (iPhone/iPad, macOS). Ссылка на App Store.
INCY_DOWNLOAD_LINK=https://apps.apple.com/app/id6756943388
# One-tap кнопка «Подключить через INCY». Пусто = кнопки нет.
# Значение: https://<домен-бота>/incy?url={subscription_link}
INCY_CRYPTOLINK_REDIRECT_TEMPLATE=
# Email в карточке поддержки (копируемым текстом). Пусто = строка скрыта.
SUPPORT_EMAIL=
```

- [ ] **Step 4: Verify settings import**

Run: `py -3.13 -c "from app.config import settings; print(settings.get_incy_download_link(), settings.get_incy_cryptolink_redirect_template(), repr(settings.get_support_email()))"`
Expected: `https://apps.apple.com/app/id6756943388 None ''`

- [ ] **Step 5: Commit**

```bash
git add app/config.py .env.example
git commit -m "feat(config): add INCY download/redirect and SUPPORT_EMAIL settings"
```

---

## Task 2: INCY deep-link scheme + redirect helper

**Files:**
- Modify: `app/utils/subscription_utils.py:61-109`
- Test: `tests/utils/test_incy_scheme.py`

- [ ] **Step 1: Write the failing test**

Создать `tests/utils/test_incy_scheme.py`:

```python
from app.utils.subscription_utils import convert_subscription_link_to_incy_scheme


def test_https_link_wrapped_in_incy_add():
    result = convert_subscription_link_to_incy_scheme('https://sub.freekov.net/abc')
    assert result == 'incy://add/https://sub.freekov.net/abc'


def test_incy_scheme_passed_through():
    assert convert_subscription_link_to_incy_scheme('incy://add/x') == 'incy://add/x'


def test_empty_returns_none():
    assert convert_subscription_link_to_incy_scheme('') is None
    assert convert_subscription_link_to_incy_scheme(None) is None


def test_non_http_returns_none():
    assert convert_subscription_link_to_incy_scheme('ftp://x') is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/utils/test_incy_scheme.py -v`
Expected: FAIL — `ImportError: cannot import name 'convert_subscription_link_to_incy_scheme'`

- [ ] **Step 3: Refactor happ redirect helper to shared builder + add INCY functions**

В `app/utils/subscription_utils.py` заменить `get_happ_cryptolink_redirect_link` (строки 61-89) на:

```python
def _build_cryptolink_redirect_link(subscription_link: str, template: str) -> str:
    encoded_link = quote(subscription_link, safe='')
    replacements = {
        '{subscription_link}': encoded_link,
        '{link}': encoded_link,
        '{subscription_link_raw}': subscription_link,
        '{link_raw}': subscription_link,
    }

    replaced = False
    for placeholder, value in replacements.items():
        if placeholder in template:
            template = template.replace(placeholder, value)
            replaced = True

    if replaced:
        return template

    if template.endswith(('=', '?', '&')):
        return f'{template}{encoded_link}'

    return f'{template}{encoded_link}'


def get_happ_cryptolink_redirect_link(subscription_link: str | None) -> str | None:
    if not subscription_link:
        return None

    template = settings.get_happ_cryptolink_redirect_template()
    if not template:
        return None

    return _build_cryptolink_redirect_link(subscription_link, template)


def get_incy_redirect_link(subscription_link: str | None) -> str | None:
    if not subscription_link:
        return None

    template = settings.get_incy_cryptolink_redirect_template()
    if not template:
        return None

    return _build_cryptolink_redirect_link(subscription_link, template)
```

После `convert_subscription_link_to_happ_scheme` (после строки 109) добавить:

```python
def convert_subscription_link_to_incy_scheme(subscription_link: str | None) -> str | None:
    """Build an INCY deep link that imports the subscription.

    INCY uses the same import convention as Happ: ``incy://add/<plain https url>``
    with the PLAIN https subscription URL. A already-``incy://`` link is returned
    as-is.
    """
    if not subscription_link:
        return None

    link = subscription_link.strip()
    if link.lower().startswith('incy://'):
        return link
    if link.lower().startswith(('http://', 'https://')):
        return f'incy://add/{link}'
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/utils/test_incy_scheme.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/utils/subscription_utils.py tests/utils/test_incy_scheme.py
git commit -m "feat: INCY deep-link scheme and redirect-link helper"
```

---

## Task 3: /incy web redirect route

**Files:**
- Modify: `app/webserver/unified_app.py:18` (import), `:27` (render fn), `:319-331` (routes)

- [ ] **Step 1: Import INCY converter**

В `app/webserver/unified_app.py` строку 18 заменить:

```python
from app.utils.subscription_utils import (
    convert_subscription_link_to_happ_scheme,
    convert_subscription_link_to_incy_scheme,
)
```

- [ ] **Step 2: Generalize the redirect render function**

Заменить сигнатуру и тело `_render_happ_redirect_page` (строки 27-85) — переименовать в `_render_app_redirect_page(deep_link, app_name='Happ')` и параметризовать название приложения:

```python
def _render_app_redirect_page(deep_link: str | None, app_name: str = 'Happ') -> tuple[str, int]:
    """Build the HTML page that bounces the browser into the target app.

    Telegram inline-keyboard URL buttons only accept http/https/tg:// schemes,
    so a one-tap "Подключиться" button cannot point at a custom scheme directly.
    Instead the button points at this https endpoint, which forwards to the
    app scheme (``happ://`` / ``incy://``). iOS Safari and Telegram's in-app
    browser often refuse to auto-open a custom scheme without a user gesture, so
    we attempt an automatic redirect AND always render a manual button fallback.

    Returns ``(html, status_code)``.
    """
    import html as _html
    import json as _json

    if not deep_link:
        page = (
            '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Ссылка недоступна</title></head>'
            '<body style="font-family:sans-serif;text-align:center;padding:2rem;">'
            '<h2>⚠️ Ссылка подписки недоступна</h2>'
            '<p>Вернитесь в бота и откройте подключение заново.</p>'
            '</body></html>'
        )
        return page, status.HTTP_400_BAD_REQUEST

    href = _html.escape(deep_link, quote=True)
    js_link = _json.dumps(deep_link)
    name = _html.escape(app_name)
    page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url={href}">
<title>Подключение через {name}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#111; color:#eee;
         display:flex; min-height:100vh; margin:0; align-items:center; justify-content:center; }}
  .card {{ text-align:center; padding:2rem; max-width:420px; }}
  h1 {{ font-size:1.4rem; margin-bottom:.5rem; }}
  p {{ color:#aaa; line-height:1.5; }}
  a.btn {{ display:inline-block; margin-top:1.2rem; padding:.9rem 1.6rem; border-radius:12px;
           background:#4c8bf5; color:#fff; text-decoration:none; font-weight:600; font-size:1.05rem; }}
</style>
</head>
<body>
<div class="card">
  <h1>🔗 Открываем {name}…</h1>
  <p>Если приложение не открылось автоматически, нажмите кнопку ниже.</p>
  <a class="btn" href="{href}">Открыть в {name}</a>
</div>
<script>
  window.location.replace({js_link});
</script>
</body>
</html>"""
    return page, status.HTTP_200_OK
```

- [ ] **Step 3: Update /happ route and add /incy route**

Заменить `/happ` роут (строки 319-331) на оба роута:

```python
    @app.get('/happ', include_in_schema=False)
    async def happ_redirect(url: str = '') -> HTMLResponse:  # pragma: no cover - thin redirect endpoint
        subscription_link = (url or '').strip()
        happ_link: str | None = None
        if subscription_link.lower().startswith(('http://', 'https://', 'happ://')):
            happ_link = convert_subscription_link_to_happ_scheme(subscription_link)

        page, status_code = _render_app_redirect_page(happ_link, 'Happ')
        return HTMLResponse(
            content=page,
            status_code=status_code,
            headers={'Cache-Control': 'no-store'},
        )

    # INCY deep-link redirect (iPhone/iPad, macOS). Зеркало /happ: Telegram не
    # принимает схему incy:// в URL-кнопках, поэтому кнопка ведёт сюда, а роут
    # перебрасывает в приложение INCY. Включается INCY_CRYPTOLINK_REDIRECT_TEMPLATE
    # (https://<домен-бота>/incy?url={subscription_link}).
    @app.get('/incy', include_in_schema=False)
    async def incy_redirect(url: str = '') -> HTMLResponse:  # pragma: no cover - thin redirect endpoint
        subscription_link = (url or '').strip()
        incy_link: str | None = None
        if subscription_link.lower().startswith(('http://', 'https://', 'incy://')):
            incy_link = convert_subscription_link_to_incy_scheme(subscription_link)

        page, status_code = _render_app_redirect_page(incy_link, 'INCY')
        return HTMLResponse(
            content=page,
            status_code=status_code,
            headers={'Cache-Control': 'no-store'},
        )
```

- [ ] **Step 4: Verify module imports cleanly**

Run: `py -3.13 -c "import ast; ast.parse(open('app/webserver/unified_app.py', encoding='utf-8').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add app/webserver/unified_app.py
git commit -m "feat(web): add /incy deep-link redirect route"
```

---

## Task 4: Connect screen builder

**Files:**
- Create: `app/utils/connect_screen.py`
- Test: `tests/utils/test_connect_screen.py`

- [ ] **Step 1: Write the failing test**

Создать `tests/utils/test_connect_screen.py`:

```python
from app.localization.texts import get_texts
from app.utils.connect_screen import build_connect_screen


def _urls(rows):
    return [b.url for row in rows for b in row if b.url]


def _callbacks(rows):
    return [b.callback_data for row in rows for b in row if b.callback_data]


def _texts():
    return get_texts('ru')


def test_full_screen_has_both_apps_and_buttons():
    caption, rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
        happ_windows_url='https://happ/win.exe',
        incy_url='https://apps.apple.com/incy',
        subscription_link='https://sub.freekov.net/abc',
        happ_redirect_url='https://bot/happ?url=x',
        incy_redirect_url='https://bot/incy?url=x',
    )
    assert 'Подключение' in caption
    assert 'https://play.google.com/happ' in caption
    assert 'https://happ/win.exe' in caption
    assert 'https://apps.apple.com/incy' in caption
    assert 'https://sub.freekov.net/abc' in caption
    urls = _urls(rows)
    assert 'https://bot/happ?url=x' in urls
    assert 'https://bot/incy?url=x' in urls
    assert 'back_to_menu' in _callbacks(rows)


def test_incy_button_hidden_without_redirect():
    caption, rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
        happ_windows_url='',
        incy_url='https://apps.apple.com/incy',
        subscription_link='https://sub/abc',
        happ_redirect_url='https://bot/happ?url=x',
        incy_redirect_url='',
    )
    urls = _urls(rows)
    assert 'https://bot/happ?url=x' in urls
    assert all('incy' not in u for u in urls)


def test_copy_block_hidden_without_link():
    caption, rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
        happ_windows_url='',
        incy_url='',
        subscription_link='',
        happ_redirect_url='',
        incy_redirect_url='',
    )
    assert '<code>' not in caption
    assert _callbacks(rows) == ['back_to_menu']


def test_back_button_always_last():
    caption, rows = build_connect_screen(_texts())
    assert rows[-1][0].callback_data == 'back_to_menu'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/utils/test_connect_screen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.utils.connect_screen'`

- [ ] **Step 3: Create the builder**

Создать `app/utils/connect_screen.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/utils/test_connect_screen.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/utils/connect_screen.py tests/utils/test_connect_screen.py
git commit -m "feat: connect-screen builder (Happ + INCY)"
```

---

## Task 5: Wire connect screen into handler

**Files:**
- Modify: `app/handlers/subscription/purchase.py:810-870` (`show_install_guide_devices`)

- [ ] **Step 1: Replace the handler body**

Заменить `show_install_guide_devices` (строки 810-870) на:

```python
async def show_install_guide_devices(callback: types.CallbackQuery, db_user: User, db: AsyncSession):
    """Экран «Подключиться»: приложения Happ/INCY + ссылка подписки + one-tap кнопки."""
    texts = get_texts(db_user.language)

    from app.utils.connect_screen import build_connect_screen
    from app.utils.subscription_utils import (
        get_display_subscription_link,
        get_happ_cryptolink_redirect_link,
        get_incy_redirect_link,
    )

    subscription = getattr(db_user, 'subscription', None)
    link = get_display_subscription_link(subscription) if subscription else None

    caption, rows = build_connect_screen(
        texts,
        happ_android_url=settings.get_happ_download_link('android') or '',
        happ_windows_url=settings.get_happ_download_link('windows') or '',
        incy_url=settings.get_incy_download_link() or '',
        subscription_link=link or '',
        happ_redirect_url=(get_happ_cryptolink_redirect_link(link) or '') if link else '',
        incy_redirect_url=(get_incy_redirect_link(link) or '') if link else '',
    )

    await _show_guide_screen(callback, caption, types.InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()
```

Примечание: `_HAPP_DOWNLOAD_PLATFORMS` (строки 788-793) больше не используется этим хендлером — удалить константу, если на неё нет других ссылок (проверить: `grep -rn "_HAPP_DOWNLOAD_PLATFORMS" app/`).

- [ ] **Step 2: Verify module parses and no stale references**

Run: `py -3.13 -c "import ast; ast.parse(open('app/handlers/subscription/purchase.py', encoding='utf-8').read()); print('ok')"`
Expected: `ok`

Run: `grep -rn "_HAPP_DOWNLOAD_PLATFORMS" app/`
Expected: пусто (после удаления) либо только определение — тогда удалить его.

- [ ] **Step 3: Commit**

```bash
git add app/handlers/subscription/purchase.py
git commit -m "feat: render connect screen via builder (Happ + INCY)"
```

---

## Task 6: Support card builder

**Files:**
- Create: `app/utils/support_screen.py`
- Test: `tests/utils/test_support_screen.py`

- [ ] **Step 1: Write the failing test**

Создать `tests/utils/test_support_screen.py`:

```python
from app.localization.texts import get_texts
from app.utils.support_screen import build_support_screen


def _urls(rows):
    return [b.url for row in rows for b in row if b.url]


def _callbacks(rows):
    return [b.callback_data for row in rows for b in row if b.callback_data]


def _texts():
    return get_texts('ru')


def test_full_card_has_three_channels():
    caption, rows = build_support_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='https://t.me/FreakVPN_SupportBot',
        support_email='FreakVPNsp@outlook.com',
        tickets_enabled=True,
    )
    assert 'Служба поддержки' in caption
    assert '@FreakVPN_SupportBot' in caption
    assert 'FreakVPNsp@outlook.com' in caption
    assert '<code>FreakVPNsp@outlook.com</code>' in caption
    urls = _urls(rows)
    cbs = _callbacks(rows)
    assert 'https://t.me/FreakVPN_SupportBot' in urls
    assert 'support_request' in cbs
    assert cbs[-1] == 'menu_info'


def test_email_hidden_when_empty():
    caption, rows = build_support_screen(
        _texts(),
        support_username='@x',
        support_url='https://t.me/x',
        support_email='',
        tickets_enabled=True,
    )
    assert 'outlook' not in caption
    assert '<code>' not in caption


def test_ticket_button_hidden_when_disabled():
    caption, rows = build_support_screen(
        _texts(),
        support_username='@x',
        support_url='https://t.me/x',
        support_email='',
        tickets_enabled=False,
    )
    assert 'support_request' not in _callbacks(rows)


def test_back_button_goes_to_info_and_is_last():
    caption, rows = build_support_screen(_texts())
    assert rows[-1][0].callback_data == 'menu_info'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/utils/test_support_screen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.utils.support_screen'`

- [ ] **Step 3: Create the builder**

Создать `app/utils/support_screen.py`:

```python
"""Билдер карточки «Служба поддержки» (классический бот FreekVPN).

Чистая функция: получает готовые настройки (username/url/email, включены ли
тикеты) и возвращает caption + ряды кнопок. Три канала как в веб-кабинете:
Telegram, email (копируемым текстом — Telegram не открывает mailto из кнопок)
и создание обращения (существующий флоу support_request → тикет).
"""

from __future__ import annotations

from aiogram import types


def build_support_screen(
    texts,
    *,
    support_username: str = '',
    support_url: str = '',
    support_email: str = '',
    tickets_enabled: bool = False,
) -> tuple[str, list[list[types.InlineKeyboardButton]]]:
    header = texts.t('SUPPORT_CARD_TITLE', '<b>Служба поддержки</b>')
    intro = texts.t(
        'SUPPORT_CARD_INTRO',
        'Возникли вопросы по подписке, оплате или подключению? Напишите нам удобным способом.',
    )
    caption = header
    if intro:
        caption += f'\n\n{intro}'

    lines: list[str] = []
    if support_url:
        username = (support_username or '').strip() or support_url
        lines.append(
            texts.t('SUPPORT_CARD_TELEGRAM', 'Telegram: {username}').format(username=username)
        )
    if support_email:
        lines.append(
            texts.t('SUPPORT_CARD_EMAIL', 'Электронная почта: <code>{email}</code>').format(email=support_email)
        )
    if tickets_enabled:
        lines.append(
            texts.t(
                'SUPPORT_CARD_TICKET',
                'Создать обращение: опишите проблему — обычно отвечаем в течение часа',
            )
        )
    if lines:
        caption += '\n\n' + '\n'.join(lines)

    rows: list[list[types.InlineKeyboardButton]] = []
    if support_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('SUPPORT_CARD_WRITE_BTN', 'Написать'),
                url=support_url,
            )
        ])
    if tickets_enabled:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('SUPPORT_CARD_TICKET_BTN', 'Создать обращение'),
                callback_data='support_request',
            )
        ])
    rows.append([
        types.InlineKeyboardButton(
            text=texts.t('MENU_BACK_BUTTON', '← Назад'),
            callback_data='menu_info',
        )
    ])
    return caption, rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/utils/test_support_screen.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/utils/support_screen.py tests/utils/test_support_screen.py
git commit -m "feat: support-card builder (Telegram + email + ticket)"
```

---

## Task 7: Wire support card + info-screen entry

**Files:**
- Modify: `app/handlers/support.py:27-36` (`show_support_info`)
- Modify: `app/utils/info_help_screen.py:70-76` (support button)
- Modify: `tests/handlers/test_info_help_screen.py`

- [ ] **Step 1: Update the info-screen test for the new callback**

В `tests/handlers/test_info_help_screen.py`:

В `test_full_screen_has_all_links_and_buttons` заменить строку
`assert 'https://t.me/FreakVPN_SupportBot' in urls` на:

```python
    assert 'menu_support' in _callbacks(rows)
```

В `test_documents_hidden_when_no_url` заменить строку
`assert _urls(rows) == ['https://t.me/FreakVPN_SupportBot']` на:

```python
    assert _urls(rows) == []
    assert 'menu_support' in _callbacks(rows)
```

- [ ] **Step 2: Run info-screen test to verify it now fails**

Run: `py -3.13 -m pytest tests/handlers/test_info_help_screen.py -v`
Expected: FAIL (support button всё ещё url, callbacks не содержат `menu_support`)

- [ ] **Step 3: Change info-screen support button to callback**

В `app/utils/info_help_screen.py` заменить блок кнопки поддержки (строки 70-76):

```python
    if support_url:
        rows.append([
            types.InlineKeyboardButton(
                text=texts.t('INFO_MENU_SUPPORT', 'Поддержка'),
                callback_data='menu_support',
            )
        ])
```

- [ ] **Step 4: Run info-screen test to verify it passes**

Run: `py -3.13 -m pytest tests/handlers/test_info_help_screen.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Replace show_support_info body**

В `app/handlers/support.py` заменить `show_support_info` (строки 27-36):

```python
async def show_support_info(callback: types.CallbackQuery, db_user: User):
    texts = get_texts(db_user.language)

    from app.utils.support_screen import build_support_screen

    tickets_enabled = SupportSettingsService.is_tickets_enabled()
    caption, rows = build_support_screen(
        texts,
        support_username=settings.SUPPORT_USERNAME or '',
        support_url=settings.get_support_contact_url() or '',
        support_email=settings.get_support_email(),
        tickets_enabled=tickets_enabled,
    )
    await edit_or_answer_photo(
        callback=callback,
        caption=caption,
        keyboard=types.InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode='HTML',
    )
    await callback.answer()
```

Удалить теперь неиспользуемый импорт `get_support_keyboard` из строки 9, если он не нужен другим функциям в файле (проверить: `grep -n get_support_keyboard app/handlers/support.py`).

- [ ] **Step 6: Verify support module parses**

Run: `py -3.13 -c "import ast; ast.parse(open('app/handlers/support.py', encoding='utf-8').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add app/handlers/support.py app/utils/info_help_screen.py tests/handlers/test_info_help_screen.py
git commit -m "feat: support card via builder; info screen opens it via menu_support"
```

---

## Task 8: Promocode button in buy flow

**Files:**
- Modify: `app/handlers/subscription/tariff_purchase.py:247-266` (`get_tariffs_keyboard`), `:269-300` (`get_tariff_periods_keyboard`)
- Test: `tests/utils/test_promocode_button.py`

- [ ] **Step 1: Write the failing test**

Создать `tests/utils/test_promocode_button.py`:

```python
from types import SimpleNamespace

from app.handlers.subscription.tariff_purchase import (
    get_tariff_periods_keyboard,
    get_tariffs_keyboard,
)


def _callbacks(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row if b.callback_data]


def test_tariffs_keyboard_has_promocode_button():
    tariffs = [SimpleNamespace(id=1, name='Test')]
    kb = get_tariffs_keyboard(tariffs, 'ru')
    cbs = _callbacks(kb)
    assert 'menu_promocode' in cbs
    # промокод перед кнопкой «Назад»
    assert cbs.index('menu_promocode') < cbs.index('back_to_menu')


def test_periods_keyboard_has_promocode_button():
    tariff = SimpleNamespace(id=1, period_prices={'30': 10000})
    kb = get_tariff_periods_keyboard(tariff, 'ru', db_user=None, back_callback='back_to_menu')
    cbs = _callbacks(kb)
    assert 'menu_promocode' in cbs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/utils/test_promocode_button.py -v`
Expected: FAIL — `assert 'menu_promocode' in cbs` (кнопки ещё нет)

- [ ] **Step 3: Add the promocode row to both keyboards**

В `get_tariffs_keyboard` (строка 264) заменить:

```python
    buttons.append([InlineKeyboardButton(text=texts.BACK, callback_data='back_to_menu')])
```

на:

```python
    buttons.append([
        InlineKeyboardButton(
            text=texts.t('MENU_HAVE_PROMOCODE', '🎟️ У меня есть промокод'),
            callback_data='menu_promocode',
        )
    ])
    buttons.append([InlineKeyboardButton(text=texts.BACK, callback_data='back_to_menu')])
```

В `get_tariff_periods_keyboard` (строка 298) заменить:

```python
    buttons.append([InlineKeyboardButton(text=texts.BACK, callback_data=back_callback)])
```

на:

```python
    buttons.append([
        InlineKeyboardButton(
            text=texts.t('MENU_HAVE_PROMOCODE', '🎟️ У меня есть промокод'),
            callback_data='menu_promocode',
        )
    ])
    buttons.append([InlineKeyboardButton(text=texts.BACK, callback_data=back_callback)])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/utils/test_promocode_button.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/handlers/subscription/tariff_purchase.py tests/utils/test_promocode_button.py
git commit -m "feat: promocode entry button in tariff purchase screens"
```

---

## Task 9: Full test sweep

- [ ] **Step 1: Run all new tests together**

Run: `py -3.13 -m pytest tests/utils/test_incy_scheme.py tests/utils/test_connect_screen.py tests/utils/test_support_screen.py tests/utils/test_promocode_button.py tests/handlers/test_info_help_screen.py -v`
Expected: все PASS (18 passed)

- [ ] **Step 2: Sanity-parse all modified modules**

Run:
```bash
for f in app/config.py app/utils/subscription_utils.py app/webserver/unified_app.py app/handlers/subscription/purchase.py app/handlers/support.py app/utils/info_help_screen.py app/handlers/subscription/tariff_purchase.py app/utils/connect_screen.py app/utils/support_screen.py; do py -3.13 -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$f" && echo "ok $f"; done
```
Expected: `ok` для каждого файла.

---

## Owner deploy notes (после мержа)

- В боевой `.env`: `INCY_CRYPTOLINK_REDIRECT_TEMPLATE=https://<домен>/incy?url={subscription_link}`, `SUPPORT_EMAIL=FreakVPNsp@outlook.com`; проверить `SUPPORT_USERNAME=@FreakVPN_SupportBot`, `HAPP_DOWNLOAD_LINK_ANDROID/WINDOWS`, `SUPPORT_SYSTEM_MODE` с тикетами.
- Реверс-прокси: пробросить путь `/incy` на порт бота 8080 (рядом с `/happ`).
- `git pull` + `docker compose up -d --build`; тексты при желании переопределить в `../ru-locales-live.json` + scp.
- Проверка на тестовом боте: экран «Подключиться» (обе кнопки), карточка поддержки из Инфо, кнопка промокода в оплате.
