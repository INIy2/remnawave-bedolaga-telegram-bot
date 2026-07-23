from app.localization.texts import get_texts
from app.utils.info_help_screen import build_help_contacts_screen


def _urls(rows):
    return [b.url for row in rows for b in row if b.url]


def _callbacks(rows):
    return [b.callback_data for row in rows for b in row if b.callback_data]


def _texts():
    return get_texts('ru')


def test_full_screen_has_support_channels_docs_and_ticket_button():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='https://t.me/FreakVPN_SupportBot',
        support_email='FreakVPNsp@outlook.com',
        privacy_url='https://telegra.ph/privacy',
        agreement_url='https://telegra.ph/agreement',
        tickets_enabled=True,
    )
    assert 'Помощь и контакты' in caption
    assert '@FreakVPN_SupportBot' in caption
    assert '<code>FreakVPNsp@outlook.com</code>' in caption
    assert 'Создать обращение' in caption  # строка про тикет
    assert 'https://telegra.ph/privacy' in caption
    assert 'https://telegra.ph/agreement' in caption

    urls = _urls(rows)
    cbs = _callbacks(rows)
    assert 'support_request' in cbs
    assert 'https://telegra.ph/privacy' in urls
    assert 'https://telegra.ph/agreement' in urls
    # Прямой кнопки-ссылки на поддержку больше нет
    assert 'https://t.me/FreakVPN_SupportBot' not in urls
    assert cbs[-1] == 'back_to_menu'


def test_email_and_ticket_hidden_when_absent():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='@x',
        support_url='https://t.me/x',
        support_email='',
        privacy_url='',
        agreement_url='',
        tickets_enabled=False,
    )
    assert '<code>' not in caption
    assert 'Создать обращение' not in caption
    assert 'support_request' not in _callbacks(rows)


def test_documents_hidden_when_no_url():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='https://t.me/FreakVPN_SupportBot',
        support_email='',
        privacy_url='',
        agreement_url='',
        tickets_enabled=False,
    )
    assert 'telegra.ph' not in caption
    assert _urls(rows) == []
    assert 'back_to_menu' in _callbacks(rows)


def test_back_button_always_last():
    _caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='',
        support_url='',
        support_email='',
        privacy_url='',
        agreement_url='',
        tickets_enabled=False,
    )
    assert rows[-1][0].callback_data == 'back_to_menu'
