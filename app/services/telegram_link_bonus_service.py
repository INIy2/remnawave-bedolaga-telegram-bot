"""Bonus subscription days for linking Telegram to a cabinet account.

A linked Telegram account is worth more to us than a Telegram login button: it is
how the bot reaches the user afterwards (expiry warnings, payment receipts, support).
So we pay for it in days of service.

The bonus is granted once per account — see ``User.telegram_link_bonus_granted_at``.
Collecting it repeatedly by unlinking would otherwise be trivial. Attaching one
Telegram account to several cabinet accounts is already blocked upstream: the
linking route sends that case into the account-merge flow instead.
"""

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.crud.subscription import (
    create_trial_subscription,
    extend_subscription,
    get_subscription_by_user_id,
)
from app.database.models import User
from app.services.subscription_service import SubscriptionService


logger = structlog.get_logger(__name__)

TELEGRAM_LINK_BONUS_DAYS = 3


async def grant_telegram_link_bonus(db: AsyncSession, user: User) -> dict | None:
    """Grant the one-time Telegram-link bonus.

    Returns ``{'bonus_days': int, 'trial_started': bool}``, or None when nothing
    was granted (already claimed, or no Telegram linked).

    Never raises: the caller has already linked the account and committed, and a
    failed bonus must not turn a successful link into an error response.
    """
    if user.telegram_id is None or user.telegram_link_bonus_granted_at is not None:
        return None

    days = TELEGRAM_LINK_BONUS_DAYS
    subscription_service = SubscriptionService()
    trial_started = False

    try:
        subscription = await get_subscription_by_user_id(db, user.id)

        if subscription:
            await extend_subscription(db, subscription, days)
            # The panel keeps its own expiry date, so an extension that is not
            # pushed there leaves the user with days the VPN itself won't honour.
            await subscription_service.update_remnawave_user(db, subscription)
        else:
            # No subscription at all means the trial is still untouched (any
            # subscription blocks it — see User.is_trial_already_used). Handing out
            # a bare 3-day subscription here would silently burn a 14-day trial, so
            # start the trial instead and put the bonus days on top of it.
            trial_started = not user.has_had_paid_subscription
            duration = settings.TRIAL_DURATION_DAYS + days if trial_started else days
            subscription = await create_trial_subscription(db, user.id, duration_days=duration)
            panel_user = await subscription_service.create_remnawave_user(db, subscription)
            if panel_user is None and subscription_service.is_configured:
                # create_remnawave_user swallows API errors and returns None. Rather
                # than hand out a subscription with no working config, hand it to the
                # retry queue — the days stay, the config arrives shortly after.
                from app.services.remnawave_retry_queue import remnawave_retry_queue

                remnawave_retry_queue.enqueue(
                    subscription_id=subscription.id,
                    user_id=user.id,
                    action='create',
                )
                logger.warning(
                    'Telegram link bonus: RemnaWave user not provisioned, enqueued for retry',
                    user_id=user.id,
                    subscription_id=subscription.id,
                )

        user.telegram_link_bonus_granted_at = datetime.now(UTC)
        await db.commit()
    except Exception as error:
        await db.rollback()
        logger.error(
            'Failed to grant Telegram link bonus',
            user_id=user.id,
            telegram_id=user.telegram_id,
            error=error,
        )
        return None

    logger.info(
        'Telegram link bonus granted',
        user_id=user.id,
        telegram_id=user.telegram_id,
        days=days,
        trial_started=trial_started,
    )
    return {'bonus_days': days, 'trial_started': trial_started}
