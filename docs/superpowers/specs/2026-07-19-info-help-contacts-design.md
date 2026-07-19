# Спека: инфо-экран «Помощь и контакты» (FreekVPN)

Дата: 2026-07-19
Ветка: `feature/bot-redesign-onboarding`

## Цель

Переработать инфо-экран классического бота (`show_info_menu`) в единый экран
«Помощь и контакты»: быстрые ссылки в тексте + те же пункты в виде кнопок.
Политику конфиденциальности и Пользовательское соглашение вынести на
telegra.ph (Instant View по ссылке). Поддержку перенаправить на внешний бот
`@FreakVPN_SupportBot`, тикет-поддержку внутри бота скрыть (не вырезать).

## Экран (`app/handlers/menu.py`, `show_info_menu`, ~строка 457)

**Текст (caption, HTML):**

```
💡 <b>Помощь и контакты</b>
<blockquote>Если что-то непонятно — здесь все быстрые ссылки.</blockquote>

• Поддержка: <a href="{support_url}">@FreakVPN_SupportBot</a>
• Кабинет: подписка, баланс и установка — в главном меню

• Политика конфиденциальности: <a href="{privacy_url}">читать</a>
• Пользовательское соглашение: <a href="{agreement_url}">читать</a>
```

**Кнопки под текстом (то же в виде кнопок):**

- `💬 Поддержка` → url = `get_support_contact_url()`
- `🔒 Политика конфиденциальности` → url = `PRIVACY_POLICY_URL`
- `📄 Пользовательское соглашение` → url = `USER_AGREEMENT_URL`
- `← Назад` → callback `back_to_menu`

**Правила показа (гейтинг):**

- Строка «Поддержка» и её кнопка — только если `get_support_contact_url()`
  не пуст **и** поддержка включена (`SupportSettingsService.is_support_menu_enabled()`
  / `SUPPORT_MENU_ENABLED`).
- Строка «Политика» и её кнопка — только если `PRIVACY_POLICY_URL` задан.
- Строка «Соглашение» и её кнопка — только если `USER_AGREEMENT_URL` задан.
- Строка «Кабинет» — статичная, всегда.
- FAQ — убрать из экрана полностью.
- Пункт «Публичная оферта» (`menu_public_offer`) на этом экране заменяется
  «Пользовательским соглашением» (внешняя ссылка).

Текст-строки собираются так, чтобы пустой (незаданный) пункт не оставлял
висящей строки в caption.

## Источник контента: telegra.ph через конфиг

Две новых настройки в `app/config.py` (+ `.env.example`):

- `PRIVACY_POLICY_URL: str = ''` — telegra.ph-ссылка на Политику.
- `USER_AGREEMENT_URL: str = ''` — telegra.ph-ссылка на Соглашение.

Прод-значения (в реальный `.env` на сервере):

- `PRIVACY_POLICY_URL=https://telegra.ph/Politika-konfidencialnosti-FreekVPN-07-19`
- `USER_AGREEMENT_URL=https://telegra.ph/Polzovatelskoe-soglashenie-FreekVPN-07-19`

Старая БД-пагинация Политики/Оферты (`menu_public_offer` / `menu_privacy_policy`
и их хендлеры в `menu.py`) **остаётся в коде** — инфо-экран на неё больше не
ссылается. Ничего не удаляем.

## Поддержка → внешний бот, тикеты скрываем

- Кнопка/ссылка «Поддержка» ведёт на `@FreakVPN_SupportBot` через
  `SUPPORT_USERNAME` + существующий `get_support_contact_url()`.
- Прод-значение: `SUPPORT_USERNAME=@FreakVPN_SupportBot` в реальном `.env`.
- Тикет-хендлеры (`app/handlers/tickets.py`) и админка тикетов **остаются в
  коде**, но вход из инфо-экрана на `support_request` убран.

## Где что живёт (деплой)

- **Тексты** (заголовок, blockquote, шаблоны строк, подписи кнопок) →
  локаль-ключи. Правятся через `../ru-locales-live.json` (мастер, scp) +
  дефолт в `app/localization/locales/ru.json`.
  Новые ключи (имена ориентировочные):
  - `INFO_HELP_HEADER` = `💡 <b>Помощь и контакты</b>`
  - `INFO_HELP_INTRO` = blockquote-строка
  - `INFO_HELP_SUPPORT_LINE`, `INFO_HELP_CABINET_LINE`,
    `INFO_HELP_PRIVACY_LINE`, `INFO_HELP_AGREEMENT_LINE`
  - подписи кнопок: `INFO_MENU_SUPPORT` (есть), `INFO_MENU_PRIVACY` (есть),
    новый `INFO_MENU_AGREEMENT` = `📄 Пользовательское соглашение`
  - слово-ссылка `INFO_HELP_READ` = `читать`
- **Ссылки/контакт** → реальный `.env` на сервере:
  `SUPPORT_USERNAME`, `PRIVACY_POLICY_URL`, `USER_AGREEMENT_URL`.
- **Код** → git pull + docker build.

## Действия владельца перед деплоем

1. Создать две telegra.ph-страницы (уже созданы, URL выше).
2. В `.env`: `SUPPORT_USERNAME=@FreakVPN_SupportBot`,
   `PRIVACY_POLICY_URL=...`, `USER_AGREEMENT_URL=...`.
3. Убедиться, что `SUPPORT_MENU_ENABLED=true` (дефолт).
4. Залить `../ru-locales-live.json` (с новыми ключами) на сервер поверх
   `locales/ru.json`.

## Вне scope

- Полное удаление тикет-подсистемы.
- Изменение механики Политики/Оферты в админке (остаётся, просто не на этом экране).
- Изменение других экранов меню.
