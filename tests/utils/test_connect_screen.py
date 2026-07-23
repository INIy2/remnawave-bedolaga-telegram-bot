from app.localization.texts import get_texts
from app.utils.connect_screen import build_connect_screen


def _urls(rows):
    return [b.url for row in rows for b in row if b.url]


def _callbacks(rows):
    return [b.callback_data for row in rows for b in row if b.callback_data]


def _texts():
    return get_texts('ru')


def test_full_screen_has_both_apps_all_platforms_and_buttons():
    caption, rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
        happ_windows_url='https://happ/win.exe',
        incy_url='https://apps.apple.com/incy',
        incy_android_url='https://play.google.com/incy',
        incy_windows_url='https://incy/win.exe',
        subscription_link='https://sub.freekov.net/abc',
        happ_redirect_url='https://bot/happ?url=x',
        incy_redirect_url='https://bot/incy?url=x',
    )
    assert 'Подключение' in caption
    # Happ block
    assert 'https://play.google.com/happ' in caption
    assert 'https://happ/win.exe' in caption
    # INCY block — все три платформы
    assert 'https://apps.apple.com/incy' in caption
    assert 'https://play.google.com/incy' in caption
    assert 'https://incy/win.exe' in caption
    assert 'https://sub.freekov.net/abc' in caption
    urls = _urls(rows)
    assert 'https://bot/happ?url=x' in urls
    assert 'https://bot/incy?url=x' in urls
    assert 'back_to_menu' in _callbacks(rows)


def test_incy_android_windows_hidden_when_unset():
    caption, rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
        happ_windows_url='',
        incy_url='https://apps.apple.com/incy',
        incy_android_url='',
        incy_windows_url='',
        subscription_link='https://sub/abc',
        happ_redirect_url='https://bot/happ?url=x',
        incy_redirect_url='',
    )
    assert 'https://apps.apple.com/incy' in caption
    # В подзаголовке INCY не должно быть Android/Windows, если ссылок нет
    assert 'INCY</b> — iPhone/iPad, macOS\n' in caption
    urls = _urls(rows)
    assert 'https://bot/happ?url=x' in urls
    assert all('incy' not in u for u in urls)


def test_hint_and_copy_block():
    caption, _rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
        subscription_link='https://sub/abc',
    )
    assert 'нажмите на подключение' in caption
    assert '<code>https://sub/abc</code>' in caption


def test_copy_block_hidden_without_link():
    caption, rows = build_connect_screen(
        _texts(),
        happ_android_url='https://play.google.com/happ',
    )
    assert '<code>' not in caption
    assert _callbacks(rows) == ['back_to_menu']


def test_back_button_always_last():
    _caption, rows = build_connect_screen(_texts())
    assert rows[-1][0].callback_data == 'back_to_menu'
