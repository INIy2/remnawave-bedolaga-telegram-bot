# FreekVPN — экран подключения, поддержка, промокод (дизайн)

Ветка `feature/bot-redesign-onboarding`. Три доработки классического бота, приводящие
интерфейс в соответствие с веб-кабинетом (`D:\JS\Bedolaga_site\bedolaga-cabinet`).

Связанные заметки: онбординг/меню/Happ, «Помощь и контакты».

## Контекст (что уже есть в коде)

- **Промокоды реализованы полностью** — `app/handlers/promocode.py` (`menu_promocode`,
  активация, rate-limit, мульти-тариф, дни/скидка/баланс, админка). При редизайне
  кнопку убрали из меню (комментарий в `app/keyboards/inline.py:610`). Нужна только точка входа.
- **Поддержка и тикеты реализованы** — `app/handlers/support.py` (`menu_support` →
  `show_support_info`; `support_request` → категории → тикет) + `tickets.py`;
  `SUPPORT_SYSTEM_MODE = tickets | contact | both`; гейтинг через `SupportSettingsService`.
- **`/happ`-редирект** — `app/webserver/unified_app.py`, роут `GET /happ`,
  `_render_happ_redirect_page` + `convert_subscription_link_to_happ_scheme` (`happ://add/<url>`),
  ссылка строится `get_happ_cryptolink_redirect_link` из `HAPP_CRYPTOLINK_REDIRECT_TEMPLATE`.
- **Экран подключения** — `show_install_guide_devices` (callback `install_guide`) в
  `app/handlers/subscription/purchase.py`: одно сообщение, ссылки Happ по платформам
  текстом + одна кнопка «Подключиться».
- Референс ссылок/deep-link — `bedolaga-cabinet/src/content/connectGuide.ts`:
  INCY для iOS/macOS (`incy://add/{url}`), Happ для Android/Windows (`happ://add/{url}`).

## 1. Экран подключения (`install_guide`)

Переписать тело `show_install_guide_devices`. Компактный экран, сгруппированный по
**приложениям** (не по платформам-табам — Telegram их не поддерживает нативно).

**Текст (caption, HTML):**
- Заголовок `📲 <b>Подключение</b>` + короткая подсказка «выбери приложение под платформу».
- Блок **Happ** — Android · Windows, ссылки «скачать» из
  `settings.get_happ_download_link('android'|'windows')`. Строка показывается только для
  тех платформ, где ссылка задана.
- Блок **INCY** — iPhone/iPad · macOS, одна ссылка App Store из нового `INCY_DOWNLOAD_LINK`.
- Копируемая ссылка подписки в `<blockquote expandable><code>…</code></blockquote>`
  (как сейчас), при наличии подписки.

**Кнопки:**
- `🔌 Подключить через Happ` → `get_happ_cryptolink_redirect_link(link)` (существующий
  `/happ`). Показывается только если шаблон задан и ссылка есть.
- `🔌 Подключить через INCY` → новый `get_incy_redirect_link(link)` (`/incy`).
  Показывается только если `INCY_CRYPTOLINK_REDIRECT_TEMPLATE` задан и ссылка есть.
- `⬅️ В главное меню` → `back_to_menu`.

Рендер прежним `_show_guide_screen` (картинка-логотип + caption). Видео-плейсхолдер
`INSTALL_VIDEO_PATH` и комментарий как вернуть видео — сохранить.

### Web-роут `/incy`

Добавить `GET /incy` в `unified_app.py`, зеркало `/happ`:
- `convert_subscription_link_to_incy_scheme(link)` → `incy://add/<plain https url>`
  (уже-`incy://` пробрасывается как есть).
- Рендер HTML-страницы редиректа: обобщить `_render_happ_redirect_page` до параметра
  схемы/названия приложения (или добавить тонкий аналог), заголовок «Подключение через INCY».
- Роут публичный, `include_in_schema=False`, принимает `?url=`, конвертит, отдаёт страницу.

### Хелпер redirect-ссылки INCY

`get_incy_redirect_link(subscription_link)` в `subscription_utils.py` — копия
`get_happ_cryptolink_redirect_link`, но берёт `settings.get_incy_cryptolink_redirect_template()`.
Пустой шаблон → `None` → кнопка INCY не рисуется.

## 2. Экран поддержки (`menu_support` → карточка «Служба поддержки»)

Переверстать `show_support_info` под 3 канала (как на сайте):

**Текст (caption, HTML):**
- Заголовок `<b>Служба поддержки</b>` + строка «Возникли вопросы по подписке, оплате
  или подключению? Напишите нам удобным способом.»
- **Telegram** — `@FreakVPN_SupportBot` (из `SUPPORT_USERNAME`), если задан.
- **Электронная почта** — `FreakVPNsp@outlook.com` копируемым `<code>` (без кнопки —
  Telegram не открывает `mailto:` из inline-кнопок), если задан новый `SUPPORT_EMAIL`.
- **Создать обращение** — «Опишите проблему — обычно отвечаем в течение часа»
  (только если тикеты включены).

**Кнопки:**
- `Написать` (url на `https://t.me/<username>` без `@`) — если `SUPPORT_USERNAME` задан.
- `Создать обращение` → callback `support_request` (существующий флоу категория→тикет),
  если `SupportSettingsService.is_tickets_enabled()`.
- `← Назад` → `menu_info`.

Каждый канал/кнопка независимо скрывается, если его настройка пуста/выключена.

**Wiring:** в инфо-экране «Помощь и контакты» (`app/utils/info_help_screen.py`) кнопка
«Поддержка» — сменить с url на callback `menu_support`, чтобы открывалась новая карточка.
Хендлер `show_support_info` уже слушает `menu_support`.

## 3. Промокод в оплате

`menu_promocode` готов. Добавить кнопку `🎟️ У меня есть промокод` → `menu_promocode`
в экран списка тарифов (`show_tariffs_list`, флоу `menu_buy`). Точное место кнопки
(над/под списком тарифов, отдельный ряд) — определить при написании плана по фактической
структуре клавиатуры.

## Конфиг и тексты

**Новые настройки** (`app/config.py` + `.env.example`, пустой дефолт → элемент скрыт):
- `INCY_DOWNLOAD_LINK: str = 'https://apps.apple.com/app/id6756943388'` — App Store,
  покрывает iOS и macOS.
- `INCY_CRYPTOLINK_REDIRECT_TEMPLATE: str = ''` — дефолт пусто; owner ставит
  `https://<домен-бота>/incy?url={subscription_link}`. + геттер `get_incy_cryptolink_redirect_template()`.
- `SUPPORT_EMAIL: str = ''` — дефолт пусто; owner ставит `FreakVPNsp@outlook.com`.

**Переиспользуются:** `HAPP_DOWNLOAD_LINK_*`, `HAPP_CRYPTOLINK_REDIRECT_TEMPLATE`,
`SUPPORT_USERNAME`, `SUPPORT_SYSTEM_MODE`.

**Тексты** — дефолтами в коде через `texts.t('KEY', 'дефолт')` и/или
`app/localization/locales/ru.json`, чтобы владелец мог переопределить через живой
`../ru-locales-live.json`. Кнопки без эмодзи там, где принято в редизайне.

## Тестирование

- Юнит-тесты на чистые билдеры: конвертер `incy://add/…`, сборка экрана подключения
  (какие блоки/кнопки при заданных/пустых настройках), сборка карточки поддержки
  (3 канала × включён/выключен). Гонять `py -3.13 -m pytest` (системный python 3.10 не
  тянет `conftest.py`).
- Ручная проверка на тестовом боте после деплоя (как делали ранее): экран подключения,
  обе connect-кнопки, поддержка, кнопка промокода в оплате.

## Владельцу перед деплоем (его часть)

- В реальный `.env`: `INCY_CRYPTOLINK_REDIRECT_TEMPLATE=https://<домен>/incy?url={subscription_link}`,
  `SUPPORT_EMAIL=FreakVPNsp@outlook.com`; убедиться, что `SUPPORT_USERNAME=@FreakVPN_SupportBot`,
  `HAPP_DOWNLOAD_LINK_ANDROID/WINDOWS` заданы, `SUPPORT_SYSTEM_MODE` включает тикеты.
- Проброс пути `/incy` в реверс-прокси на порт бота 8080 (рядом с уже проброшенным `/happ`).
- `git pull` + `docker compose up -d --build`; при переопределении текстов — правки в
  `../ru-locales-live.json` + scp.

## Вне scope

- Автоопределение платформы (в боте нет user-agent).
- Изменение логики активации промокодов, начислений, системы тикетов.
- Веб-кабинет/MiniApp.
