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
    flat = [b for row in kb.inline_keyboard for b in row]
    idx_trial = next(i for i, b in enumerate(flat) if b.callback_data == 'trial_activate')
    idx_pay = next(i for i, b in enumerate(flat) if b.callback_data == 'menu_buy')
    assert idx_trial < idx_pay


def test_menu_no_trial_button_when_unavailable(monkeypatch):
    monkeypatch.setattr(type(settings), 'is_cabinet_mode', lambda self: False)
    kb = get_main_menu_keyboard(language='ru', trial_available=False)
    assert _trial_button(kb) is None
