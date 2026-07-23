from app.localization.texts import get_texts
from app.utils.info_help_screen import build_help_contacts_screen


def _urls(rows):
    return [b.url for row in rows for b in row if b.url]


def _callbacks(rows):
    return [b.callback_data for row in rows for b in row if b.callback_data]


def _texts():
    return get_texts('ru')


def test_full_screen_has_all_links_and_buttons():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='https://t.me/FreakVPN_SupportBot',
        privacy_url='https://telegra.ph/privacy',
        agreement_url='https://telegra.ph/agreement',
    )

    assert 'Помощь и контакты' in caption
    assert '<blockquote>' in caption
    assert '@FreakVPN_SupportBot' in caption
    assert 'https://telegra.ph/privacy' in caption
    assert 'https://telegra.ph/agreement' in caption

    urls = _urls(rows)
    assert 'menu_support' in _callbacks(rows)
    assert 'https://telegra.ph/privacy' in urls
    assert 'https://telegra.ph/agreement' in urls
    assert 'back_to_menu' in _callbacks(rows)


def test_support_hidden_when_no_url():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='',
        privacy_url='https://telegra.ph/privacy',
        agreement_url='https://telegra.ph/agreement',
    )
    assert '@FreakVPN_SupportBot' not in caption
    assert 'https://t.me/FreakVPN_SupportBot' not in _urls(rows)
    # Кабинет-строка остаётся
    assert 'Кабинет' in caption


def test_documents_hidden_when_no_url():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='@FreakVPN_SupportBot',
        support_url='https://t.me/FreakVPN_SupportBot',
        privacy_url='',
        agreement_url='',
    )
    assert 'telegra.ph' not in caption
    assert _urls(rows) == []
    assert 'menu_support' in _callbacks(rows)
    assert 'back_to_menu' in _callbacks(rows)


def test_back_button_always_present():
    caption, rows = build_help_contacts_screen(
        _texts(),
        support_username='',
        support_url='',
        privacy_url='',
        agreement_url='',
    )
    assert 'back_to_menu' in _callbacks(rows)
    assert rows[-1][0].callback_data == 'back_to_menu'
