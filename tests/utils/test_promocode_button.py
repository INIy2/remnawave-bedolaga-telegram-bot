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
