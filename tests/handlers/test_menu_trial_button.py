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
