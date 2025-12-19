"""add_session_tracking_and_progress_fields

Revision ID: 5b48f96a1c39
Revises: c2d2b8e72e7d
Create Date: 2025-12-19 14:19:24.583446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b48f96a1c39'
down_revision: Union[str, Sequence[str], None] = 'c2d2b8e72e7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
