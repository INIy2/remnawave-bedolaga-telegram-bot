"""Экран-гейт онбординга: подписка на канал + согласие с документами.

Гейт стоит перед созданием пользователя, поэтому его обход = регистрация без
подписки и без согласия. Тесты держат обе двери закрытыми.
"""

import pytest

from app.config import settings
from app.handlers import start as start_handlers
from app.keyboards.inline import get_onboarding_gate_keyboard, get_post_registration_keyboard
from app.states import RegistrationStates


async def _noop(*args, **kwargs):
    return None


class _FakeState:
    def __init__(self, data=None):
        self._data = dict(data or {})
        self.state = None

    async def get_data(self):
        return dict(self._data)

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def set_state(self, state):
        self.state = state


class _FakeMessage:
    def __init__(self):
        self.bot = object()
        self.answers = []
        self.markups = []

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.answers.append((text, reply_markup))

    async def edit_reply_markup(self, reply_markup=None):
        self.markups.append(reply_markup)


class _FakeFromUser:
    id = 555


class _FakeCallback:
    def __init__(self):
        self.message = _FakeMessage()
        self.from_user = _FakeFromUser()
        self.bot = object()
        self.alerts = []

    async def answer(self, text=None, show_alert=False):
        self.alerts.append((text, show_alert))


CHANNEL = {'channel_id': '-100500', 'channel_link': 'https://t.me/FreakVPN_Official', 'title': None}


def _button(kb, *, callback_data=None, url=None):
    for row in kb.inline_keyboard:
        for btn in row:
            if callback_data and btn.callback_data == callback_data:
                return btn
            if url and btn.url == url:
                return btn
    return None


def test_gate_keyboard_has_channel_documents_and_accept(monkeypatch):
    monkeypatch.setattr(settings, 'PRIVACY_POLICY_URL', 'https://telegra.ph/privacy')
    monkeypatch.setattr(settings, 'USER_AGREEMENT_URL', 'https://telegra.ph/agreement')

    kb = get_onboarding_gate_keyboard([CHANNEL], 'ru')

    assert _button(kb, url='https://t.me/FreakVPN_Official') is not None
    assert _button(kb, url='https://telegra.ph/privacy') is not None
    assert _button(kb, url='https://telegra.ph/agreement') is not None
    assert _button(kb, callback_data='onboarding_gate_accept') is not None


def test_gate_keyboard_skips_missing_document_links(monkeypatch):
    monkeypatch.setattr(settings, 'PRIVACY_POLICY_URL', '')
    monkeypatch.setattr(settings, 'USER_AGREEMENT_URL', '')

    kb = get_onboarding_gate_keyboard([CHANNEL], 'ru')
    urls = [b.url for row in kb.inline_keyboard for b in row if b.url]

    assert urls == ['https://t.me/FreakVPN_Official']


def test_trial_button_takes_days_from_settings(monkeypatch):
    class _Texts:
        def t(self, key, default=None):
            return '🎁 Активировать {days} дней'

    monkeypatch.setattr('app.keyboards.inline.get_texts', lambda language: _Texts())
    monkeypatch.setattr(settings, 'TRIAL_DURATION_DAYS', 7)

    kb = get_post_registration_keyboard('ru')

    assert kb.inline_keyboard[0][0].text == '🎁 Активировать 7 дней'


@pytest.mark.asyncio
async def test_gate_not_shown_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, 'ONBOARDING_GATE_ENABLED', False)
    message, state = _FakeMessage(), _FakeState()

    assert await start_handlers._show_onboarding_gate(message, 555, state, 'ru') is False
    assert message.answers == []


@pytest.mark.asyncio
async def test_gate_not_shown_without_channels_and_documents(monkeypatch):
    monkeypatch.setattr(settings, 'ONBOARDING_GATE_ENABLED', True)
    monkeypatch.setattr(settings, 'PRIVACY_POLICY_URL', '')
    monkeypatch.setattr(settings, 'USER_AGREEMENT_URL', '')

    async def _no_channels(telegram_id, bot):
        return []

    monkeypatch.setattr(start_handlers, '_get_onboarding_gate_channels', _no_channels)
    message, state = _FakeMessage(), _FakeState()

    assert await start_handlers._show_onboarding_gate(message, 555, state, 'ru') is False
    assert message.answers == []


@pytest.mark.asyncio
async def test_gate_shown_and_registration_paused(monkeypatch):
    monkeypatch.setattr(settings, 'ONBOARDING_GATE_ENABLED', True)
    monkeypatch.setattr(settings, 'PRIVACY_POLICY_URL', 'https://telegra.ph/privacy')
    monkeypatch.setattr(settings, 'USER_AGREEMENT_URL', 'https://telegra.ph/agreement')

    async def _channels(telegram_id, bot):
        return [CHANNEL]

    monkeypatch.setattr(start_handlers, '_get_onboarding_gate_channels', _channels)
    message, state = _FakeMessage(), _FakeState()

    assert await start_handlers._show_onboarding_gate(message, 555, state, 'ru') is True
    assert len(message.answers) == 1
    assert state.state == RegistrationStates.waiting_for_onboarding_gate


@pytest.mark.asyncio
async def test_gate_not_reshown_after_passing(monkeypatch):
    monkeypatch.setattr(settings, 'ONBOARDING_GATE_ENABLED', True)
    message = _FakeMessage()
    state = _FakeState({'onboarding_gate_passed': True})

    assert await start_handlers._show_onboarding_gate(message, 555, state, 'ru') is False
    assert message.answers == []


@pytest.mark.asyncio
async def test_accept_blocks_when_not_subscribed(monkeypatch):
    async def _channels(telegram_id, bot):
        return [dict(CHANNEL, is_subscribed=False)]

    async def _fail_continue(**kwargs):
        raise AssertionError('регистрация не должна продолжаться без подписки')

    monkeypatch.setattr(start_handlers, '_get_onboarding_gate_channels', _channels)
    monkeypatch.setattr(start_handlers, '_continue_registration_after_language', _fail_continue)
    monkeypatch.setattr(start_handlers.channel_subscription_service, 'invalidate_user_cache', _noop)

    callback, state = _FakeCallback(), _FakeState({'language': 'ru'})
    await start_handlers.process_onboarding_gate_accept(callback, state, db=None)

    assert callback.alerts and callback.alerts[0][1] is True
    assert 'onboarding_gate_passed' not in await state.get_data()


@pytest.mark.asyncio
async def test_accept_records_documents_and_continues(monkeypatch):
    monkeypatch.setattr(settings, 'PRIVACY_POLICY_URL', 'https://telegra.ph/privacy')
    monkeypatch.setattr(settings, 'USER_AGREEMENT_URL', 'https://telegra.ph/agreement')

    async def _channels(telegram_id, bot):
        return [dict(CHANNEL, is_subscribed=True)]

    continued = {}

    async def _continue(*, message, callback, state, db):
        continued['called'] = True

    monkeypatch.setattr(start_handlers, '_get_onboarding_gate_channels', _channels)
    monkeypatch.setattr(start_handlers, '_continue_registration_after_language', _continue)
    monkeypatch.setattr(start_handlers.channel_subscription_service, 'invalidate_user_cache', _noop)

    callback, state = _FakeCallback(), _FakeState({'language': 'ru'})
    await start_handlers.process_onboarding_gate_accept(callback, state, db=None)

    data = await state.get_data()
    assert continued.get('called') is True
    assert data['onboarding_gate_passed'] is True
    assert data['onboarding_consent_documents'] == ['privacy_policy', 'user_agreement']


@pytest.mark.asyncio
async def test_consent_written_only_after_gate(monkeypatch):
    recorded = []

    async def _record(db, user, documents, *, source, ip_address=None, commit=True):
        recorded.append((documents, source))

    monkeypatch.setattr(start_handlers.legal_consent_service, 'record_consent', _record)

    user = type('_User', (), {'id': 42})()
    await start_handlers._record_onboarding_consent(None, _FakeState(), user)
    assert recorded == []

    state = _FakeState({'onboarding_consent_documents': ['privacy_policy', 'user_agreement']})
    await start_handlers._record_onboarding_consent(None, state, user)
    assert recorded == [(['privacy_policy', 'user_agreement'], 'bot_registration')]
