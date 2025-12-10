"""add_case_number_to_cases

Revision ID: c2d2b8e72e7d
Revises: 66d3bb32bf00
Create Date: 2025-12-10 19:43:36.760256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d2b8e72e7d'
down_revision: Union[str, Sequence[str], None] = '66d3bb32bf00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('cases', sa.Column('case_number', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('cases', 'case_number')
