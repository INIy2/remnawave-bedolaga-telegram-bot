from app.localization.texts import get_texts
from app.utils.connect_screen import build_connect_screen


def _urls(rows):
    return [b.url for row in rows for b in row if b.url]


def _callbacks(rows):
    return [b.callback_data for row in rows for b in row if b.callback_data]


def _texts():
    return get_texts('ru')


def test_full_screen_has_both_apps_and_buttons():
    caption, rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
        happ_windows_url='https://happ/win.exe',
        incy_url='https://apps.apple.com/incy',
        subscription_link='https://sub.freekov.net/abc',
        happ_redirect_url='https://bot/happ?url=x',
        incy_redirect_url='https://bot/incy?url=x',
    )
    assert 'Подключение' in caption
    assert 'https://play.google.com/happ' in caption
    assert 'https://happ/win.exe' in caption
    assert 'https://apps.apple.com/incy' in caption
    assert 'https://sub.freekov.net/abc' in caption
    urls = _urls(rows)
    assert 'https://bot/happ?url=x' in urls
    assert 'https://bot/incy?url=x' in urls
    assert 'back_to_menu' in _callbacks(rows)


def test_incy_button_hidden_without_redirect():
    caption, rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
        happ_windows_url='',
        incy_url='https://apps.apple.com/incy',
        subscription_link='https://sub/abc',
        happ_redirect_url='https://bot/happ?url=x',
        incy_redirect_url='',
    )
    urls = _urls(rows)
    assert 'https://bot/happ?url=x' in urls
    assert all('incy' not in u for u in urls)


def test_copy_block_hidden_without_link():
    caption, rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
        happ_windows_url='',
        incy_url='',
        subscription_link='',
        happ_redirect_url='',
        incy_redirect_url='',
    )
    assert '<code>' not in caption
    assert _callbacks(rows) == ['back_to_menu']


def test_back_button_always_last():
    caption, rows = build_connect_screen(_texts())
    assert rows[-1][0].callback_data == 'back_to_menu'
