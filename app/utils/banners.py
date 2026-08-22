"""Подбор баннера под раздел бота.

Бот глобально подменяет `Message.answer` и `Message.edit_text` (см. `message_patch`),
чтобы к каждому экрану прицепилась картинка. К моменту, когда патч срабатывает,
контекста хендлера уже нет, поэтому баннер нельзя выбрать в точке вызова — их
больше тридцати, и часть экранов рисуется вообще без явного вызова.

Поэтому раздел определяется один раз в мидлваре по callback-данным входящего
апдейта и кладётся в ContextVar, а патч читает его оттуда.

Файл раздела ищется как `<BANNERS_DIR>/<ключ>.png`. Файла нет — возвращаем None,
и вызывающий код откатывается на обычный `LOGO_FILE`. Поэтому код безопасно
выкатывать до того, как картинки окажутся на сервере.
"""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path

from app.config import settings

# Ключ = имя файла без расширения в BANNERS_DIR.
BANNER_KEYS = ('main', 'payment', 'connect', 'referral', 'info', 'support')

_current_banner: ContextVar[str | None] = ContextVar('current_banner', default=None)

# Порядок важен: выигрывает первое совпадение по префиксу.
#
# `None` означает «раздела нет, оставить обычный логотип». Админка стоит первой
# именно поэтому: `admin_payment_check_` не должен утащить баннер оплаты в
# админские экраны.
BANNER_RULES: tuple[tuple[str | None, tuple[str, ...]], ...] = (
    (None, ('admin_', 'backup_', 'squad_', 'sqd_', 'promo_group_', 'promo_offer_', 'user_messages_')),
    (
        'connect',
        (
            'subscription_connect',
            'subscription_happ_download',
            'subscription_manage_devices',
            'subscription_reset_devices',
            'device_connection_help',
            'device_guide_',
            'device_rename',
            'devices_',
            'app_',
            'happ_',
            'guide_',
        ),
    ),
    (
        'payment',
        (
            'menu_balance',
            'menu_promocode',
            'balance_',
            'topup_',
            'check_',
            'buy_subscription',
            'buy_traffic',
            'simple_subscription',
            'tariff_',
            'period_',
            'traffic_',
            'switch_traffic_',
            'autopay_',
            'unlink_card_',
            'subscription_confirm',
            'subscription_extend',
            'subscription_resume_checkout',
            'subscription_add_countries',
            'subscription_change_devices',
            'subscription_switch_traffic',
            'trial_payment',
            'trial_pay_with_balance',
        ),
    ),
    ('referral', ('menu_referrals', 'referral')),
    ('support', ('menu_support', 'support_', 'ticket_', 'view_ticket_', 'my_tickets')),
    (
        'info',
        (
            'menu_info',
            'menu_faq',
            'menu_rules',
            'menu_privacy_policy',
            'menu_public_offer',
            'menu_server_status',
            'menu_language',
        ),
    ),
    ('main', ('back_to_menu', 'main_menu', 'menu_profile', 'menu_subscription', 'menu_trial', 'trial_activate')),
)

# Команды, с которых начинается работа с ботом, — им отдаём «Главную».
_MAIN_COMMANDS = ('/start', '/menu', '/help')


def resolve_banner_key(data: str | None) -> str | None:
    """Определить раздел по callback-данным или тексту команды."""
    if not data:
        return None
    if data.startswith('/'):
        command = data.split()[0].split('@')[0].lower()
        return 'main' if command in _MAIN_COMMANDS else None
    for key, prefixes in BANNER_RULES:
        if data.startswith(prefixes):
            return key
    return None


def set_current_banner(key: str | None):
    """Запомнить раздел текущего апдейта. Возвращает токен для reset()."""
    return _current_banner.set(key)


def reset_current_banner(token) -> None:
    _current_banner.reset(token)


def get_current_banner() -> str | None:
    return _current_banner.get()


def banner_path(key: str | None) -> Path | None:
    """Путь к файлу баннера, если он есть на диске."""
    if not key or key not in BANNER_KEYS:
        return None
    path = Path(settings.BANNERS_DIR) / f'{key}.png'
    try:
        if path.is_file():
            return path
    except OSError:
        return None
    return None
