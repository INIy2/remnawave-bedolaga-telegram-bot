"""Раскладка экранов по баннерам разделов.

Первый заход выкатили с дырами: экран выбора периода и экран подключения
остались на общем логотипе, потому что открываются по `menu_buy` и
`install_guide`, а таких префиксов в таблице не было. Здесь два теста:
точечный — что известные экраны попадают в свой раздел, и сплошной —
что ни один зарегистрированный callback не проваливается мимо таблицы
незамеченным.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.utils.banners import BANNER_KEYS, resolve_banner_key


# (callback, ожидаемый раздел). None = сознательно на общем логотипе.
CASES = [
    ('/start', 'main'),
    ('back_to_menu', 'main'),
    ('menu_profile', 'main'),
    ('my_subscriptions', 'main'),
    ('sm:12', 'main'),
    ('menu_buy', 'payment'),
    ('tariff_select:3', 'payment'),
    ('tariff_period:3:7', 'payment'),
    ('menu_balance', 'payment'),
    ('balance_topup', 'payment'),
    ('topup_amount|platega_m2|4000', 'payment'),
    ('check_platega_abc', 'payment'),
    ('se:12', 'payment'),
    ('st:12', 'payment'),
    ('install_guide', 'connect'),
    ('subscription_connect', 'connect'),
    ('device_guide_ios', 'connect'),
    ('sl:12', 'connect'),
    ('sd:12', 'connect'),
    ('subscription_revoke', 'connect'),
    ('menu_referrals', 'referral'),
    ('referral_withdraw', 'referral'),
    ('menu_support', 'support'),
    ('create_ticket', 'support'),
    ('menu_info', 'info'),
    ('rules_accept', 'info'),
    ('language_select:en', 'info'),
    # Админка не должна утаскивать баннеры: admin_payment_check_ похож на оплату.
    ('admin_panel', None),
    ('admin_payment_check_9', None),
    ('promo_offer_send_menu_3', None),
    # Служебные, экран не рисуют.
    ('noop', None),
    (None, None),
]


@pytest.mark.parametrize(('data', 'expected'), CASES)
def test_known_screens_route_to_their_section(data, expected):
    assert resolve_banner_key(data) == expected


def test_every_key_is_known():
    for key, _prefixes in __import__('app.utils.banners', fromlist=['BANNER_RULES']).BANNER_RULES:
        assert key is None or key in BANNER_KEYS, f'неизвестный раздел: {key}'


# Callback, которые ничего не рисуют, — им баннер не нужен.
SERVICE_CALLBACKS = {'noop', 'current_page', 'cancel', 'webhook:close', 'ban_notify:delete'}

_EQ = re.compile(r"F\.data\s*(?:==\s*|\.startswith\(\s*)'([^']+)'")
_IN = re.compile(r"F\.data\.in_\(\s*\[([^\]]+)\]", re.S)
_LIT = re.compile(r"'([^']+)'")


def _registered_user_callbacks() -> set[str]:
    app_dir = Path(__file__).resolve().parents[2] / 'app'
    out: set[str] = set()
    for path in app_dir.rglob('*.py'):
        if 'admin' in path.parts:  # админка сознательно на общем логотипе
            continue
        src = path.read_text(encoding='utf-8')
        out.update(m.group(1) for m in _EQ.finditer(src))
        for block in _IN.finditer(src):
            out.update(m.group(1) for m in _LIT.finditer(block.group(1)))
    return {c for c in out if not c.startswith('admin')}


def test_no_user_screen_falls_through_unnoticed():
    """Новый экран должен либо попасть в раздел, либо быть явно признан служебным."""
    orphans = sorted(c for c in _registered_user_callbacks() if resolve_banner_key(c) is None and c not in SERVICE_CALLBACKS)
    assert not orphans, (
        'callback без раздела — добавь в BANNER_RULES или в SERVICE_CALLBACKS: ' + ', '.join(orphans)
    )
