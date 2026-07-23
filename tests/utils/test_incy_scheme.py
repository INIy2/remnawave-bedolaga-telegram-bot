from app.utils.subscription_utils import convert_subscription_link_to_incy_scheme


def test_https_link_wrapped_in_incy_add():
    result = convert_subscription_link_to_incy_scheme('https://sub.freekov.net/abc')
    assert result == 'incy://add/https://sub.freekov.net/abc'


def test_incy_scheme_passed_through():
    assert convert_subscription_link_to_incy_scheme('incy://add/x') == 'incy://add/x'


def test_empty_returns_none():
    assert convert_subscription_link_to_incy_scheme('') is None
    assert convert_subscription_link_to_incy_scheme(None) is None


def test_non_http_returns_none():
    assert convert_subscription_link_to_incy_scheme('ftp://x') is None
