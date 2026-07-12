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
    db = _make_db(existing_reward_id=555)
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

    assert result is False
