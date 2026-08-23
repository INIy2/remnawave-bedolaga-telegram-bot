"""users: mark when the Telegram-link bonus was granted

Revision ID: 0107
Revises: 0106
Create Date: 2026-08-21

Linking a Telegram account to a cabinet account grants bonus subscription days.
The bonus is once per account, so we need a durable marker: without it, a user
could unlink and relink to collect the days over and over.

The column holds the grant timestamp rather than a boolean — it costs the same
and answers "when did this happen" when someone asks about a suspicious grant.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0107'
down_revision: Union[str, None] = '0106'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'users' not in inspector.get_table_names():
        return
    existing = {col['name'] for col in inspector.get_columns('users')}
    if 'telegram_link_bonus_granted_at' not in existing:
        op.add_column(
            'users',
            sa.Column('telegram_link_bonus_granted_at', sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'users' not in inspector.get_table_names():
        return
    existing = {col['name'] for col in inspector.get_columns('users')}
    if 'telegram_link_bonus_granted_at' in existing:
        op.drop_column('users', 'telegram_link_bonus_granted_at')
