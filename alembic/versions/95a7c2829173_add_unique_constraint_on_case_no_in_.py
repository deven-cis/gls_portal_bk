"""add unique constraint on case_no in cases table

Revision ID: 95a7c2829173
Revises: d18b0e58ae5a
Create Date: 2025-12-03 17:03:10.121930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95a7c2829173'
down_revision: Union[str, Sequence[str], None] = 'd18b0e58ae5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('uq_cases_case_no', 'cases', ['case_no'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_cases_case_no', 'cases', type_='unique')
