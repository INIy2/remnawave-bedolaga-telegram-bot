# Реферальная программа на дни — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Заменить денежную реферальную механику на начисление дней подписки — реферер +3 дня, реферал +7 дней при покупке подписки рефералом от 100 ₽, разово за реферала.

**Architecture:** Новая идемпотентная функция `process_referral_subscription_reward` в `referral_service.py` вызывается из точек завершения платной покупки (после финализации подписки). Дни начисляются существующим `extend_subscription`. Одноразовость гарантирует маркер-строка `ReferralEarning(reason='referral_days_reward')`. Денежная механика глушится нулевыми дефолтами в конфиге без удаления кода.

**Tech Stack:** Python, aiogram 3.x, SQLAlchemy async, pytest (async через `pytest_pyfunc_call` в `tests/conftest.py`), unit-тесты на `SimpleNamespace` + `monkeypatch` + `AsyncMock` (образец — `tests/services/test_referral_service.py`).

**Spec:** `docs/superpowers/specs/2026-07-12-referral-days-design.md`

---

## Task 1: Конфиг — новые настройки и глушение денег

**Files:**
- Modify: `app/config.py:291-294`
- Modify: `.env.example` (реферальная секция)

- [ ] **Step 1: Добавить настройки и обнулить денежные дефолты в `app/config.py`**

Найти блок (строки ~291-294):

```python
    REFERRAL_MINIMUM_TOPUP_KOPEKS: int = 10000
    REFERRAL_FIRST_TOPUP_BONUS_KOPEKS: int = 10000
    REFERRAL_INVITER_BONUS_KOPEKS: int = 10000
    REFERRAL_COMMISSION_PERCENT: int = 25
```

Заменить на:

```python
    REFERRAL_MINIMUM_TOPUP_KOPEKS: int = 10000
    # FreekVPN: денежная реферальная механика отключена — заменена на дни подписки.
    # Нули глушат бонусы/комиссию (код гейтит на > 0), не удаляя логику. Обратимо.
    REFERRAL_FIRST_TOPUP_BONUS_KOPEKS: int = 0
    REFERRAL_INVITER_BONUS_KOPEKS: int = 0
    REFERRAL_COMMISSION_PERCENT: int = 0
    # Реферальная награда днями подписки (новая механика).
    REFERRAL_REWARD_REFERRER_DAYS: int = 3       # дней пригласившему
    REFERRAL_REWARD_REFERRED_DAYS: int = 7       # дней приглашённому
    REFERRAL_PURCHASE_THRESHOLD_KOPEKS: int = 10000  # порог покупки подписки (100 ₽)
```

- [ ] **Step 2: Задокументировать в `.env.example`**

Найти реферальную секцию `.env.example` и добавить рядом с `REFERRAL_*`:

```dotenv
# --- Реферальная программа на дни подписки (FreekVPN) ---
# Реферер получает REFERRAL_REWARD_REFERRER_DAYS дней, реферал —
# REFERRAL_REWARD_REFERRED_DAYS дней, когда реферал покупает подписку
# на сумму >= REFERRAL_PURCHASE_THRESHOLD_KOPEKS (в копейках). Разово за реферала.
# Денежная механика отключена нулями ниже.
REFERRAL_REWARD_REFERRER_DAYS=3
REFERRAL_REWARD_REFERRED_DAYS=7
REFERRAL_PURCHASE_THRESHOLD_KOPEKS=10000
REFERRAL_FIRST_TOPUP_BONUS_KOPEKS=0
REFERRAL_INVITER_BONUS_KOPEKS=0
REFERRAL_COMMISSION_PERCENT=0
```

- [ ] **Step 3: Commit**

```bash
git add app/config.py .env.example
git commit -m "feat(referral): настройки наград днями, глушение денежной механики"
```

---

## Task 2: Ядро — `process_referral_subscription_reward` (TDD)

**Files:**
- Modify: `app/services/referral_service.py` (новая функция в конце файла; импорты вверху)
- Test: `tests/services/test_referral_days_reward.py`

Функция-контракт (для справки, реализуется в Step 3):

```python
async def process_referral_subscription_reward(
    db, buyer, purchase_amount_kopeks: int, bot=None
) -> bool
```

Порядок мок-вызовов внутри (важно для тестов): `db.execute` (проверка дубля) →
`get_user_by_id` (реферер) → `get_subscription_by_user_id(buyer)` →
`extend_subscription(buyer_sub, referred_days)` → `get_subscription_by_user_id(referrer)` →
`extend_subscription(referrer_sub, referrer_days)` (или `create_trial_subscription` если подписки нет) →
`get_user_campaign_id` → `create_referral_earning`.

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/services/test_referral_days_reward.py`:

```python
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services import referral_service


def _make_db(existing_reward_id=None):
    """db.execute(...).scalar_one_or_none() -> existing_reward_id (None = дубля нет)."""
    result = SimpleNamespace(scalar_one_or_none=lambda: existing_reward_id)
    return SimpleNamespace(execute=AsyncMock(return_value=result), commit=AsyncMock())


def _patch_common(monkeypatch, referrer, buyer_sub, referrer_sub):
    monkeypatch.setattr(referral_service, 'get_user_by_id', AsyncMock(return_value=referrer))
    get_sub = AsyncMock(side_effect=[buyer_sub, referrer_sub])
    monkeypatch.setattr(referral_service, 'get_subscription_by_user_id', get_sub)
    extend = AsyncMock()
    monkeypatch.setattr(referral_service, 'extend_subscription', extend)
    create_trial = AsyncMock()
    monkeypatch.setattr(referral_service, 'create_trial_subscription', create_trial)
    earning = AsyncMock()
    monkeypatch.setattr(referral_service, 'create_referral_earning', earning)
    monkeypatch.setattr(referral_service, 'get_user_campaign_id', AsyncMock(return_value=None))
    monkeypatch.setattr(referral_service.settings, 'REFERRAL_PROGRAM_ENABLED', True)
    monkeypatch.setattr(referral_service.settings, 'REFERRAL_PURCHASE_THRESHOLD_KOPEKS', 10000)
    monkeypatch.setattr(referral_service.settings, 'REFERRAL_REWARD_REFERRER_DAYS', 3)
    monkeypatch.setattr(referral_service.settings, 'REFERRAL_REWARD_REFERRED_DAYS', 7)
    return get_sub, extend, create_trial, earning


async def test_grants_days_to_both_on_qualified_purchase(monkeypatch):
    buyer = SimpleNamespace(id=1, telegram_id=101, full_name='Buyer', referred_by_id=2)
    referrer = SimpleNamespace(id=2, telegram_id=202, full_name='Referrer')
    buyer_sub = SimpleNamespace(id=11)
    referrer_sub = SimpleNamespace(id=22)
    db = _make_db(existing_reward_id=None)
    _, extend, create_trial, earning = _patch_common(monkeypatch, referrer, buyer_sub, referrer_sub)

    result = await referral_service.process_referral_subscription_reward(db, buyer, 15000)

    assert result is True
    # buyer +7, referrer +3
    assert extend.await_count == 2
    assert extend.await_args_list[0].args[1] is buyer_sub
    assert extend.await_args_list[0].args[2] == 7
    assert extend.await_args_list[1].args[1] is referrer_sub
    assert extend.await_args_list[1].args[2] == 3
    create_trial.assert_not_awaited()
    earning.assert_awaited_once()
    assert earning.await_args.kwargs['reason'] == 'referral_days_reward'
    assert earning.await_args.kwargs['user_id'] == 2
    assert earning.await_args.kwargs['referral_id'] == 1


async def test_below_threshold_no_reward(monkeypatch):
    buyer = SimpleNamespace(id=1, telegram_id=101, full_name='Buyer', referred_by_id=2)
    referrer = SimpleNamespace(id=2, telegram_id=202, full_name='Referrer')
    db = _make_db(existing_reward_id=None)
    _, extend, _, earning = _patch_common(monkeypatch, referrer, SimpleNamespace(id=11), SimpleNamespace(id=22))

    result = await referral_service.process_referral_subscription_reward(db, buyer, 9999)

    assert result is False
    extend.assert_not_awaited()
    earning.assert_not_awaited()


async def test_one_time_gate_blocks_duplicate(monkeypatch):
    buyer = SimpleNamespace(id=1, telegram_id=101, full_name='Buyer', referred_by_id=2)
    referrer = SimpleNamespace(id=2, telegram_id=202, full_name='Referrer')
    db = _make_db(existing_reward_id=555)  # награда уже была
    _, extend, _, earning = _patch_common(monkeypatch, referrer, SimpleNamespace(id=11), SimpleNamespace(id=22))

    result = await referral_service.process_referral_subscription_reward(db, buyer, 15000)

    assert result is False
    extend.assert_not_awaited()
    earning.assert_not_awaited()


async def test_self_referral_skipped(monkeypatch):
    buyer = SimpleNamespace(id=2, telegram_id=202, full_name='Self', referred_by_id=2)
    db = _make_db(existing_reward_id=None)
    _, extend, _, earning = _patch_common(monkeypatch, buyer, None, None)

    result = await referral_service.process_referral_subscription_reward(db, buyer, 15000)

    assert result is False
    extend.assert_not_awaited()


async def test_no_referrer_skipped(monkeypatch):
    buyer = SimpleNamespace(id=1, telegram_id=101, full_name='Buyer', referred_by_id=None)
    db = _make_db(existing_reward_id=None)
    _, extend, _, earning = _patch_common(monkeypatch, None, None, None)

    result = await referral_service.process_referral_subscription_reward(db, buyer, 15000)

    assert result is False
    extend.assert_not_awaited()


async def test_program_disabled_skipped(monkeypatch):
    buyer = SimpleNamespace(id=1, telegram_id=101, full_name='Buyer', referred_by_id=2)
    referrer = SimpleNamespace(id=2, telegram_id=202, full_name='Referrer')
    db = _make_db(existing_reward_id=None)
    _patch_common(monkeypatch, referrer, SimpleNamespace(id=11), SimpleNamespace(id=22))
    monkeypatch.setattr(referral_service.settings, 'REFERRAL_PROGRAM_ENABLED', False)

    result = await referral_service.process_referral_subscription_reward(db, buyer, 15000)

    assert result is False


async def test_referrer_without_subscription_gets_created(monkeypatch):
    buyer = SimpleNamespace(id=1, telegram_id=101, full_name='Buyer', referred_by_id=2)
    referrer = SimpleNamespace(id=2, telegram_id=202, full_name='Referrer')
    buyer_sub = SimpleNamespace(id=11)
    db = _make_db(existing_reward_id=None)
    _, extend, create_trial, earning = _patch_common(monkeypatch, referrer, buyer_sub, None)

    result = await referral_service.process_referral_subscription_reward(db, buyer, 15000)

    assert result is True
    # buyer продлён (+7), referrer — создана подписка на 3 дня
    assert extend.await_count == 1
    assert extend.await_args_list[0].args[1] is buyer_sub
    create_trial.assert_awaited_once()
    assert create_trial.await_args.kwargs['duration_days'] == 3


async def test_grant_failure_does_not_raise(monkeypatch):
    buyer = SimpleNamespace(id=1, telegram_id=101, full_name='Buyer', referred_by_id=2)
    referrer = SimpleNamespace(id=2, telegram_id=202, full_name='Referrer')
    db = _make_db(existing_reward_id=None)
    _, extend, _, earning = _patch_common(monkeypatch, referrer, SimpleNamespace(id=11), SimpleNamespace(id=22))
    extend.side_effect = RuntimeError('remnawave down')

    result = await referral_service.process_referral_subscription_reward(db, buyer, 15000)

    assert result is False  # ошибка проглочена, покупка не роняется
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `python -m pytest tests/services/test_referral_days_reward.py -v`
Expected: FAIL — `AttributeError: module 'app.services.referral_service' has no attribute 'process_referral_subscription_reward'`

- [ ] **Step 3: Реализовать функцию**

В `app/services/referral_service.py` добавить импорты вверху (рядом с существующими импортами из crud):

```python
from app.database.crud.subscription import (
    create_trial_subscription,
    extend_subscription,
    get_subscription_by_user_id,
)
```

В конец файла добавить:

```python
async def process_referral_subscription_reward(
    db: AsyncSession,
    buyer: User,
    purchase_amount_kopeks: int,
    bot: Bot = None,
) -> bool:
    """Начисляет реферальные дни при покупке подписки рефералом.

    Реферер получает REFERRAL_REWARD_REFERRER_DAYS дней, реферал —
    REFERRAL_REWARD_REFERRED_DAYS дней. Разово за реферала (маркер-строка
    ReferralEarning с reason='referral_days_reward'). Вызывать ПОСЛЕ финализации
    подписки покупателя (иначе +дни перезапишутся логикой покупки). Идемпотентна —
    безопасна к повторным вызовам. Ошибки начисления проглатываются, покупку не роняют.
    """
    try:
        if not settings.is_referral_program_enabled():
            return False

        referrer_id = getattr(buyer, 'referred_by_id', None)
        if not referrer_id or referrer_id == buyer.id:
            return False

        if purchase_amount_kopeks < settings.REFERRAL_PURCHASE_THRESHOLD_KOPEKS:
            return False

        from sqlalchemy import select as _select

        existing = await db.execute(
            _select(ReferralEarning.id)
            .where(
                ReferralEarning.user_id == referrer_id,
                ReferralEarning.referral_id == buyer.id,
                ReferralEarning.reason == 'referral_days_reward',
            )
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            logger.info('Реферальная награда днями уже начислена, пропуск', buyer_id=buyer.id, referrer_id=referrer_id)
            return False

        referrer = await get_user_by_id(db, referrer_id)
        if not referrer:
            logger.error('Реферер не найден при начислении дней', referrer_id=referrer_id)
            return False

        referrer_days = settings.REFERRAL_REWARD_REFERRER_DAYS
        referred_days = settings.REFERRAL_REWARD_REFERRED_DAYS

        # +дни рефералу (buyer). Подписка только что куплена → продлеваем в конец.
        buyer_sub = await get_subscription_by_user_id(db, buyer.id)
        if buyer_sub:
            await extend_subscription(db, buyer_sub, referred_days)

        # +дни рефереру. Активная/истёкшая → extend (в конец / от «сейчас»). Нет → создаём.
        referrer_sub = await get_subscription_by_user_id(db, referrer_id)
        if referrer_sub:
            await extend_subscription(db, referrer_sub, referrer_days)
        else:
            await create_trial_subscription(db, referrer_id, duration_days=referrer_days)

        campaign_id = await get_user_campaign_id(db, buyer.id)
        await create_referral_earning(
            db=db,
            user_id=referrer_id,
            referral_id=buyer.id,
            amount_kopeks=0,
            reason='referral_days_reward',
            campaign_id=campaign_id,
        )

        logger.info(
            '🎁 Реферальные дни начислены',
            buyer_id=buyer.id,
            referrer_id=referrer_id,
            referrer_days=referrer_days,
            referred_days=referred_days,
        )

        if bot:
            try:
                await send_referral_notification(
                    bot,
                    referrer.telegram_id,
                    (
                        f'🎁 <b>Реферальный бонус!</b>\n\n'
                        f'Твой друг <b>{html.escape(buyer.full_name)}</b> оформил подписку — '
                        f'тебе начислено <b>+{referrer_days} дн.</b> VPN 🚀'
                    ),
                    user=referrer,
                    referral_name=buyer.full_name,
                )
                await send_referral_notification(
                    bot,
                    buyer.telegram_id,
                    (
                        f'🎁 <b>Бонус за покупку!</b>\n\n'
                        f'Как приглашённому другу тебе начислено <b>+{referred_days} дн.</b> VPN 🚀'
                    ),
                    user=buyer,
                )
            except Exception as notify_error:
                logger.error('Ошибка отправки уведомления о реф-днях', notify_error=notify_error)

        return True

    except Exception as e:
        logger.error('Ошибка начисления реферальных дней', error=e, buyer_id=getattr(buyer, 'id', None))
        return False
```

Примечание: `ReferralEarning`, `get_user_by_id`, `create_referral_earning`, `get_user_campaign_id`, `send_referral_notification`, `settings`, `logger`, `html` — уже импортированы/определены в модуле (используются существующими функциями). Проверить, что `html` импортирован (в файле уже есть `html.escape`).

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/services/test_referral_days_reward.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/referral_service.py tests/services/test_referral_days_reward.py
git commit -m "feat(referral): начисление дней подписки за реферала + тесты"
```

---

## Task 3: Статистика экрана — `qualified_count` в summary

**Files:**
- Modify: `app/utils/user_utils.py` (функция `get_user_referral_summary`, блок формирования результата)
- Test: `tests/services/test_referral_days_reward.py` (добавить тест на summary)

- [ ] **Step 1: Добавить `qualified_count` в возвращаемый dict**

В `get_user_referral_summary`, где формируется `earnings_by_type` и итоговый возврат,
добавить в возвращаемый словарь (рядом с `invited_count`):

```python
        qualified_count = earnings_by_type.get('referral_days_reward', {}).get('count', 0)
```

и включить `'qualified_count': qualified_count,` в возвращаемый dict. Найти `return {` в функции и добавить ключ.

- [ ] **Step 2: Тест на summary-ключ**

Добавить в `tests/services/test_referral_days_reward.py` (в конец) — smoke-тест, что ключ присутствует, через мок db с earnings_by_type. Если структура `get_user_referral_summary` не поддаётся простому мокингу (много запросов), пометить проверку как ручную в Task 7 и пропустить этот шаг. В таком случае — просто убедиться визуально, что ключ добавлен в возврат.

- [ ] **Step 3: Commit**

```bash
git add app/utils/user_utils.py tests/services/test_referral_days_reward.py
git commit -m "feat(referral): qualified_count в реферальной сводке"
```

---

## Task 4: Экран рефералки — убрать баннер, новый текст

**Files:**
- Modify: `app/handlers/referral.py:34-103` (функция `show_referral_info`)

- [ ] **Step 1: Переписать текст экрана**

В `show_referral_info` заменить блок формирования `referral_text` (строки ~52-66) на:

```python
    referrer_days = settings.REFERRAL_REWARD_REFERRER_DAYS
    referred_days = settings.REFERRAL_REWARD_REFERRED_DAYS
    threshold_rub = settings.REFERRAL_PURCHASE_THRESHOLD_KOPEKS // 100
    qualified = summary.get('qualified_count', 0)
    earned_days = qualified * referrer_days

    referral_text = (
        texts.t('REFERRAL_INVITE_HEADER', '👥 Приглашай друзей — получай дни VPN 🎁')
        + '\n\n'
        + texts.t(
            'REFERRAL_DAYS_RULES',
            'За каждого друга, который оформит подписку от {threshold} ₽:\n'
            '• ты получишь +{referrer} дн.\n'
            '• друг получит +{referred} дн.',
        ).format(threshold=threshold_rub, referrer=referrer_days, referred=referred_days)
        + '\n\n'
        + texts.t('REFERRAL_INVITED_LINE', 'Приглашено: {count}').format(count=summary['invited_count'])
        + '\n'
        + texts.t('REFERRAL_QUALIFIED_LINE', 'Оформили подписку: {count}').format(count=qualified)
        + '\n'
        + texts.t('REFERRAL_EARNED_DAYS_LINE', 'Тебе начислено: {days} дн.').format(days=earned_days)
        + '\n\n'
        + f'<code>{html_escape(bot_referral_link)}</code>'
    )
```

Удалить строку с `REFERRAL_TEMPORARILY_DISABLED_NOTICE` (баннер «ВРЕМЕННО НЕ РАБОТАЕТ»).
Оставить блоки `share_text`, `share_url`, `keyboard`, `edit_or_answer_photo` без изменений.

- [ ] **Step 2: Проверить импорт settings**

Убедиться, что в `app/handlers/referral.py` есть `from app.config import settings` (уже есть, строка 15).

- [ ] **Step 3: Синтаксическая проверка**

Run: `python -c "import ast; ast.parse(open('app/handlers/referral.py', encoding='utf-8').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/handlers/referral.py
git commit -m "feat(referral): экран рефералки на дни, убран баннер-заглушка"
```

---

## Task 5: Тексты уведомлений при регистрации — с денег на дни

**Files:**
- Modify: `app/services/referral_service.py:629-666` (блок `if bot:` в `process_referral_registration`)

- [ ] **Step 1: Переписать уведомления регистрации**

В `process_referral_registration`, внутри `if bot:` заменить формирование
`referral_notification` и `inviter_notification` (строки ~631-663) на:

```python
            referrer_days = settings.REFERRAL_REWARD_REFERRER_DAYS
            referred_days = settings.REFERRAL_REWARD_REFERRED_DAYS
            threshold_rub = settings.REFERRAL_PURCHASE_THRESHOLD_KOPEKS // 100

            referral_notification = (
                f'🎉 <b>Добро пожаловать!</b>\n\n'
                f'Ты перешёл по ссылке пользователя <b>{html.escape(referrer.full_name)}</b>.\n\n'
                f'💎 Оформи подписку от {threshold_rub} ₽ — получишь <b>+{referred_days} дн.</b> VPN в подарок!'
            )
            await send_referral_notification(bot, new_user.telegram_id, referral_notification, user=new_user)

            inviter_notification = (
                f'👥 <b>Новый реферал!</b>\n\n'
                f'По твоей ссылке зарегистрировался <b>{html.escape(new_user.full_name)}</b>.\n\n'
                f'🎁 Когда он оформит подписку от {threshold_rub} ₽ — тебе начислим <b>+{referrer_days} дн.</b> VPN.'
            )
            await send_referral_notification(
                bot, referrer.telegram_id, inviter_notification, user=referrer, referral_name=new_user.full_name
            )
```

Удалить старый расчёт `commission_percent = get_effective_referral_commission_percent(referrer)`
и денежные ветки внутри этого `if bot:` блока (всё, что говорило про рубли/проценты).

- [ ] **Step 2: Прогнать существующие тесты referral_service**

Run: `python -m pytest tests/services/test_referral_service.py -v`
Expected: PASS (существующие тесты денежной механики топапа не затрагивают этот блок; если какой-то тест проверял текст регистрации — обновить его ожидания под новый текст).

- [ ] **Step 3: Commit**

```bash
git add app/services/referral_service.py
git commit -m "feat(referral): уведомления регистрации на дни вместо денег"
```

---

## Task 6: Вкрутить начисление в точки завершения покупки

**Files:**
- Modify: `app/handlers/subscription/purchase.py` (после финализации подписки в `confirm_purchase`, район 2574+)
- Modify: `app/handlers/simple_subscription.py` (после финализации, район 455 и 2203)
- Modify: `app/cabinet/routes/subscription_modules/purchase.py:471` и `app/webapi/routes/miniapp.py:5587` (после успешного `submit_purchase`)

Идемпотентность (маркер-строка) делает повторные/лишние вызовы безопасными.
Порог `>= 100 ₽` и one-time гейт — внутри функции, здесь фильтровать не нужно.

- [ ] **Step 1: Найти все точки платной покупки**

Run: `grep -rn "mark_as_paid_subscription=True" app/handlers app/services app/cabinet app/webapi --include=*.py`
Зафиксировать список. Для каждой точки, где покупатель — обычный пользователь (не админ-выдача),
после того как подписка ФИНАЛИЗИРОВАНА и закоммичена (`end_date` уже выставлен), добавить вызов.

- [ ] **Step 2: Вставить вызов в бот-хендлер `confirm_purchase`**

В `app/handlers/subscription/purchase.py`, в `confirm_purchase`, ПОСЛЕ финального
`await db.commit()` подписки (после блока продления, где выставлен `end_date`), добавить:

```python
        try:
            from app.services.referral_service import process_referral_subscription_reward

            await process_referral_subscription_reward(db, db_user, final_price, bot=callback.bot)
        except Exception as ref_error:
            logger.error('Ошибка начисления реф-дней после покупки', ref_error=ref_error)
```

- [ ] **Step 3: Вставить вызов в `simple_subscription.py`**

В `app/handlers/simple_subscription.py`, после финализации подписки в каждом из двух
флоу покупки (район строк 455 и 2203, после commit подписки) добавить тот же блок,
подставив локальные имена переменных суммы и покупателя:

```python
        try:
            from app.services.referral_service import process_referral_subscription_reward

            await process_referral_subscription_reward(db, db_user, final_price, bot=callback.bot)
        except Exception as ref_error:
            logger.error('Ошибка начисления реф-дней после покупки', ref_error=ref_error)
```

(имя переменной суммы — то, что передаётся в `subtract_user_balance` рядом; имя объекта
пользователя — тот же, у кого списывали баланс; `bot` — `callback.bot` или `message.bot`.)

- [ ] **Step 4: Вставить вызов в кабинет/miniapp после `submit_purchase`**

В `app/cabinet/routes/subscription_modules/purchase.py` (около строки 471) и
`app/webapi/routes/miniapp.py` (около строки 5587), ПОСЛЕ успешного
`result = await purchase_service.submit_purchase(db, context, pricing)` добавить:

```python
        try:
            from app.services.referral_service import process_referral_subscription_reward
            from app.bot_factory import create_bot

            await process_referral_subscription_reward(
                db, context.user, pricing.final_total, bot=create_bot()
            )
        except Exception as ref_error:
            logger.error('Ошибка начисления реф-дней после покупки (miniapp/cabinet)', ref_error=ref_error)
```

Если в модуле уже есть готовый bot-аксессор (`_get_bot()`), использовать его вместо `create_bot()`.
Проверить, что `logger` в модуле определён; если нет — использовать `structlog.get_logger(__name__)`.

- [ ] **Step 5: Синтаксическая проверка всех тронутых файлов**

Run:
```bash
python -c "import ast,glob; [ast.parse(open(f,encoding='utf-8').read()) for f in ['app/handlers/subscription/purchase.py','app/handlers/simple_subscription.py','app/cabinet/routes/subscription_modules/purchase.py','app/webapi/routes/miniapp.py']]; print('OK')"
```
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add app/handlers/subscription/purchase.py app/handlers/simple_subscription.py app/cabinet/routes/subscription_modules/purchase.py app/webapi/routes/miniapp.py
git commit -m "feat(referral): вызов начисления реф-дней в точках завершения покупки"
```

---

## Task 7: Полный прогон тестов и ручная проверка

**Files:** нет (проверка)

- [ ] **Step 1: Прогнать весь релевантный набор тестов**

Run: `python -m pytest tests/services/test_referral_days_reward.py tests/services/test_referral_service.py -v`
Expected: PASS (все).

- [ ] **Step 2: Полный прогон реферальных и покупочных тестов**

Run: `python -m pytest tests/ -k "referral or purchase or subscription" -q`
Expected: без новых падений (сравнить с базой до изменений при сомнениях).

- [ ] **Step 3: Ручная проверка сценария (чек-лист)**

Через тестовый прогон/стенд убедиться:
- Реферал покупает подписку ≥100 ₽ → у реферала `end_date` +7, у реферера +3.
- Реферер с истёкшей подпиской → реактивирована от «сейчас» на 3 дня.
- Повторная покупка того же реферала → второго начисления НЕТ (маркер).
- Экран рефералки: нет баннера «ВРЕМЕННО НЕ РАБОТАЕТ», показывает Приглашено/Оформили/Начислено дней.
- Покупка < 100 ₽ → начисления нет, покупка проходит.

- [ ] **Step 4: Финальный commit (если были правки после ревью)**

```bash
git add -A
git commit -m "test(referral): финальная проверка механики дней"
```
