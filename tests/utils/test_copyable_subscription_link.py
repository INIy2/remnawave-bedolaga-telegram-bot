"""Регрессия: сырой happ://crypt… не должен попадать в текст интерфейса.

История: в режиме ``CONNECT_BUTTON_MODE=happ_cryptolink`` карточка главного меню и
экран «Подключиться» печатали ``get_display_subscription_link``. Пока панель была
2.8.0, разницы не было видно — ручку шифрования оттуда удалили, поле
``subscription_crypto_link`` у всех оставалось пустым и подставлялся обычный URL.
Панель 3.0.0 снова начала отдавать ``happ.cryptoLink``, бот сохранил его при первом
же продлении — и в карточку вместо ссылки полез километровый блоб, который нельзя
ни прочитать, ни вставить руками.
"""

from types import SimpleNamespace

from app.config import settings
from app.utils.subscription_utils import (
    get_copyable_subscription_link,
    get_display_subscription_link,
)


PLAIN = 'https://sub.freekov.net/katpbV2aZkU6ESuL'
CRYPT = 'happ://crypt4/nGf3XkcYF+YCk4dUT7cA91TK6WXdEogIIME6hU2VUjs53q8'


def _subscription(crypto_link: str | None = CRYPT):
    return SimpleNamespace(subscription_url=PLAIN, subscription_crypto_link=crypto_link)


def test_copyable_link_never_returns_crypt(monkeypatch):
    monkeypatch.setattr(settings, 'CONNECT_BUTTON_MODE', 'happ_cryptolink')
    assert get_copyable_subscription_link(_subscription()) == PLAIN


def test_display_link_still_returns_crypt_for_buttons(monkeypatch):
    """Кнопке crypt по-прежнему нужен — ломать deep link нельзя."""
    monkeypatch.setattr(settings, 'CONNECT_BUTTON_MODE', 'happ_cryptolink')
    assert get_display_subscription_link(_subscription()) == CRYPT


def test_display_link_falls_back_when_panel_gave_no_crypt(monkeypatch):
    monkeypatch.setattr(settings, 'CONNECT_BUTTON_MODE', 'happ_cryptolink')
    assert get_display_subscription_link(_subscription(crypto_link=None)) == PLAIN


def test_both_return_plain_outside_cryptolink_mode(monkeypatch):
    monkeypatch.setattr(settings, 'CONNECT_BUTTON_MODE', 'miniapp_subscription')
    subscription = _subscription()
    assert get_display_subscription_link(subscription) == PLAIN
    assert get_copyable_subscription_link(subscription) == PLAIN


def test_no_subscription_is_none():
    assert get_copyable_subscription_link(None) is None
