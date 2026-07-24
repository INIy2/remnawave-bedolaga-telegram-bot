# Кнопка «Получить триал» в главном меню

Дата: 2026-07-24
Ветка: `feature/bot-redesign-onboarding`

## Проблема

После регистрации юзер видит приветствие с кнопкой «🎁 Активировать 14 дней»
(`get_post_registration_keyboard`, callback `trial_activate`). Если он её НЕ нажал
(например, отправил `/start` повторно), он попадает в главное меню, где **нет
кнопки активировать триал** — только «Оплатить». Триал становится недоступен из
интерфейса, хотя по данным он ещё положен.

Важно: данные триал НЕ теряют. `User.is_trial_already_used()` считает триал
использованным только если у юзера была платная подписка ЛИБО есть любая подписка
(кроме PENDING-триала). Зарегистрированный юзер без подписок → триал ему всё ещё
доступен. Проблема чисто в UX: кнопку негде нажать.

## Решение

Показывать в главном меню кнопку активации триала (и подсказку в статус-карточке),
когда триал ещё доступен. Кнопка ведёт на существующий `trial_activate` —
никакой новой логики активации.

## Гейт доступности

```
trial_available = settings.TRIAL_DURATION_DAYS > 0
                  and not settings.is_trial_disabled_for_user(getattr(db_user, 'auth_type', 'telegram'))
                  and not db_user.is_trial_already_used()
```

Ровно те же условия, что проверяет `activate_trial` (`purchase.py`) перед выдачей.
Значит кнопка не появится, если активация всё равно была бы отклонена. Требует
загруженного `db_user.subscriptions` (в рендере меню он уже загружен).

## Изменения UI

### 1. Кнопка в главном меню (`get_main_menu_keyboard`, `app/keyboards/inline.py`)

Когда `trial_available` — **первым рядом** добавляем кнопку:
- текст: `texts.t('MENU_MAIN_GET_TRIAL', '🎁 Получить {days} дней').format(days=settings.TRIAL_DURATION_DAYS)`
- `callback_data='trial_activate'`
- **без `style`** → дефолтная **фиолетовая** кнопка (как «Подключиться»/«Рефералы»;
  `style='success'` даёт зелёную, `style='primary'` — синюю).

Ниже — как сейчас: «Оплатить» (зелёная, `style='success'`), «Подключиться» (при
подписке), «Рефералы», «Сайт | Инфо». Когда `trial_available == False` — меню
не меняется.

### 2. Статус-карточка (`_build_main_menu_status_card`, `app/handlers/menu.py`)

Когда `trial_available` и подписки нет — вместо блока «Осталось: Подписка не активна /
Устройства / Трафик» показываем строку-приглашение:
- `texts.t('MAIN_MENU_TRIAL_INVITE', '🎁 Тебе доступно {days} дней бесплатно — забери кнопкой ниже').format(days=settings.TRIAL_DURATION_DAYS)`

Заголовок «Ваш доступ к Freek VPN» и промо-строка рефералов остаются. Когда есть
подписка (активна/истекла) — карточка как сейчас, без изменений.

## Проводка

`trial_available` вычисляется в хендлере(ах) рендера главного меню (там есть
`db_user` с загруженными `subscriptions`) и прокидывается новым булевым параметром
`trial_available: bool = False`:
- в `get_main_menu_keyboard(...)`;
- в `get_main_menu_text(user, texts, db, *, trial_available=False)` →
  `_build_main_menu_status_card(user, texts, db, *, trial_available=False)`.

Общий хелпер вычисления гейта (напр. `is_trial_available_for_user(db_user)` рядом
с рендером меню) — чтобы не дублировать условие. Значение по умолчанию `False`
для параметра означает: call-sites, которые не считают гейт, просто не показывают
кнопку/подсказку (безопасно, не ломает существующие вызовы).

Основной call-site — рендер главного меню в `app/handlers/menu.py` (там же, где
считаются `has_active_subscription` / `subscription_is_active`, ~строки 198-234).
`start.py` (`complete_registration[_from_callback]`) тоже рисует главное меню для
уже-активных юзеров — там гейт тоже посчитать и прокинуть, чтобы кнопка была
консистентна на всех входах в меню.

## Не трогаем

- `activate_trial` и весь флоу активации — переиспользуем `trial_activate`.
- Экран после регистрации (`get_post_registration_keyboard`) — там кнопка уже есть.
- Механику `is_trial_already_used()`.

## Крайние случаи

- **После активации** у юзера появляется подписка → `is_trial_already_used()` → True →
  кнопка и подсказка исчезают, «Оплатить» показывается как обычно.
- **Триал выключен глобально** (`TRIAL_DURATION_DAYS <= 0`) или для типа юзера →
  кнопка не показывается никогда.
- **Админ/модератор** — видит кнопку, если сам ещё не брал триал (гейт по юзеру).
- **Платный триал** (`get_trial_activation_charge_amount() > 0`) — кнопка ведёт на
  тот же `trial_activate`, который сам покажет экран оплаты триала. Отдельно не
  обрабатываем (поведение как у кнопки под приветствием).

## Тесты

- Хелпер гейта `is_trial_available_for_user`: True для юзера без подписок и с
  включённым триалом; False если `is_trial_already_used()` / `TRIAL_DURATION_DAYS<=0` /
  триал отключён для типа юзера.
- `get_main_menu_keyboard(..., trial_available=True)` содержит кнопку с
  `callback_data='trial_activate'` и БЕЗ `style` (фиолетовая); при
  `trial_available=False` — не содержит.
- `_build_main_menu_status_card(..., trial_available=True)` (без подписки) содержит
  строку-приглашение и НЕ содержит «Подписка не активна».
- Прогон: `py -3.13 -m pytest`.

## Деплой

Только код → `git pull` + `docker compose up -d --build`. Новых `.env` не требуется.
Тексты кнопки/подсказки можно переопределить ключами `MENU_MAIN_GET_TRIAL` /
`MAIN_MENU_TRIAL_INVITE` в `../ru-locales-live.json` (необязательно; дефолты в коде).
