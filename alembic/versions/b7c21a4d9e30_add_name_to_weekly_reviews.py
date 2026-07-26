"""add name to weekly_reviews

Revision ID: b7c21a4d9e30
Revises: f94b4f06ced4
Create Date: 2026-07-25 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c21a4d9e30'
down_revision: Union[str, Sequence[str], None] = 'f94b4f06ced4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('weekly_reviews', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('name', sa.Text(), nullable=False, server_default='')
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('weekly_reviews', schema=None) as batch_op:
        batch_op.drop_column('name')
