from app.localization.texts import get_texts
from app.utils.support_screen import build_support_screen


def _urls(rows):
    return [b.url for row in rows for b in row if b.url]


def _callbacks(rows):
    return [b.callback_data for row in rows for b in row if b.callback_data]


def _texts():
    return get_texts('ru')


def test_full_card_has_three_channels():
    caption, rows = build_support_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='https://t.me/FreakVPN_SupportBot',
        support_email='FreakVPNsp@outlook.com',
        tickets_enabled=True,
    )
    assert 'Служба поддержки' in caption
    assert '@FreakVPN_SupportBot' in caption
    assert 'FreakVPNsp@outlook.com' in caption
    assert '<code>FreakVPNsp@outlook.com</code>' in caption
    urls = _urls(rows)
    cbs = _callbacks(rows)
    assert 'https://t.me/FreakVPN_SupportBot' in urls
    assert 'support_request' in cbs
    assert cbs[-1] == 'menu_info'


def test_email_hidden_when_empty():
    caption, rows = build_support_screen(
        _texts(),
        support_username='@x',
        support_url='https://t.me/x',
        support_email='',
        tickets_enabled=True,
    )
    assert 'outlook' not in caption
    assert '<code>' not in caption


def test_ticket_button_hidden_when_disabled():
    caption, rows = build_support_screen(
        _texts(),
        support_username='@x',
        support_url='https://t.me/x',
        support_email='',
        tickets_enabled=False,
    )
    assert 'support_request' not in _callbacks(rows)


def test_back_button_goes_to_info_and_is_last():
    caption, rows = build_support_screen(_texts())
    assert rows[-1][0].callback_data == 'menu_info'
