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
    # Админка и служебные callback, которые вообще ничего не рисуют.
    (
        None,
        (
            'admin_', 'backup_', 'squad_', 'sqd_', 'promo_group_',
            'promo_offer_edit_', 'promo_offer_send', 'promo_offer_select_squad',
            'promo_offer_clear_squad', 'user_messages_',
            'noop', 'current_page', 'webhook:', 'ban_notify:',
        ),
    ),
    (
        'connect',
        (
            'subscription_connect',
            'subscription_happ_download',
            'subscription_manage_devices',
            'subscription_reset_devices',
            'subscription_revoke',
            'confirm_reset_devices',
            'reset_all_devices',
            'device_connection_help',
            'device_guide_',
            'device_management:',
            'device_rename',
            'devices_',
            'open_subscription_link',
            'install_guide',
            'app_',
            'happ_',
            'guide_',
            'sl:',  # ссылка подписки
            'sd:',  # устройства подписки
            'sr:',  # перевыпуск ключа
        ),
    ),
    (
        'payment',
        (
            'menu_balance',
            'menu_promocode',
            'menu_buy',
            'balance_',
            'topup_',
            'check_',
            'buy_subscription',
            'buy_traffic',
            'simple_subscription',
            'subscription_upgrade',
            'subscription_purchase',
            'tariff_',
            'daily_tariff_',
            'instant_switch',
            'instant_sw',
            'period_',
            'extend_period_',
            'traffic_',
            'switch_traffic_',
            'confirm_switch_traffic_',
            'no_traffic_packages',
            'add_devices_',
            'add_traffic_',
            'change_devices_',
            'change_devices_menu:',
            'confirm_change_devices_',
            'countries_',
            'country_',
            'custom_days:',
            'custom_traffic:',
            'custom_confirm:',
            'claim_discount_',
            'clear_saved_cart',
            'return_to_saved_cart',
            'saved_cards_list',
            'confirm_unlink_',
            'unlink_card_',
            'pal24_method_',
            'platega_method_',
            'payment_methods_unavailable',
            'promo_sub:',
            'promo_offer_close',
            'autopay_',
            'subscription_autopay',
            'subscription_confirm',
            'subscription_extend',
            'subscription_resume_checkout',
            'subscription_add_countries',
            'subscription_change_devices',
            'subscription_switch_traffic',
            'trial_payment',
            'trial_pay_with_balance',
            'se:',  # продление подписки
            'st:',  # трафик подписки
        ),
    ),
    ('referral', ('menu_referrals', 'referral')),
    (
        'support',
        (
            'menu_support',
            'support_',
            'ticket_',
            'view_ticket_',
            'my_tickets',
            'create_ticket',
            'cancel_ticket_',
            'reply_ticket_',
            'close_ticket_notification_',
            'user_delete_message_',
        ),
    ),
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
            'language_select:',
            'info_page:',
            'server_status_page:',
            'privacy_policy_accept',
            'privacy_policy_decline',
            'rules_accept',
            'rules_decline',
        ),
    ),
    (
        'main',
        (
            'back_to_menu',
            'main_menu',
            'menu_profile',
            'menu_subscription',
            'menu_trial',
            'trial_activate',
            'my_subscriptions',
            'subscription_settings',
            'subscription_config_back',
            'subscription_cancel',
            'subscription_reset_traffic',
            'toggle_daily_subscription_pause',
            'sub_del',
            'sm:',  # карточка подписки
            'contests_menu',
            'contest_',
            'poll_',
            'activate_button',
            'gift_activate:',
            'webauth_confirm:',
            'webauth_deny',
            'sub_channel_check',
            'confirm_reset_traffic',
        ),
    ),
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
