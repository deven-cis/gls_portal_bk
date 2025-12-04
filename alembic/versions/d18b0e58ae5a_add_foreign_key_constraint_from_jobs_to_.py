"""add foreign key constraint from jobs to cases

Revision ID: d18b0e58ae5a
Revises: 8d69123adec6
Create Date: 2025-12-03 16:58:35.745360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd18b0e58ae5a'
down_revision: Union[str, Sequence[str], None] = '8d69123adec6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First add UNIQUE constraint on case_no in cases table
    op.create_unique_constraint('uq_cases_case_no', 'cases', ['case_no'])
    # Then add foreign key constraint from jobs to cases
    op.create_foreign_key(None, 'jobs', 'cases', ['case_no'], ['case_no'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key first
    op.drop_constraint(None, 'jobs', type_='foreignkey')
    # Then remove unique constraint
    op.drop_constraint('uq_cases_case_no', 'cases', type_='unique')
