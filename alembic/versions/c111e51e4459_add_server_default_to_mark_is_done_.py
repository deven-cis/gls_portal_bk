"""add_server_default_to_mark_is_done_columns

Revision ID: c111e51e4459
Revises: d9389febbc55
Create Date: 2025-12-29 16:51:44.249165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c111e51e4459'
down_revision: Union[str, Sequence[str], None] = 'd9389febbc55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Update existing NULL values to False
    op.execute("UPDATE jobs SET mark_is_done_case = false WHERE mark_is_done_case IS NULL")
    op.execute("UPDATE jobs SET mark_is_done_witnesses = false WHERE mark_is_done_witnesses IS NULL")
    op.execute("UPDATE jobs SET mark_is_done_attorneys = false WHERE mark_is_done_attorneys IS NULL")
    op.execute("UPDATE jobs SET mark_is_done_billings = false WHERE mark_is_done_billings IS NULL")
    op.execute("UPDATE jobs SET mark_is_done_equipment_time = false WHERE mark_is_done_equipment_time IS NULL")
    
    # Add server_default to columns
    op.alter_column('jobs', 'mark_is_done_case',
                    server_default='false',
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
    op.alter_column('jobs', 'mark_is_done_witnesses',
                    server_default='false',
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
    op.alter_column('jobs', 'mark_is_done_attorneys',
                    server_default='false',
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
    op.alter_column('jobs', 'mark_is_done_billings',
                    server_default='false',
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
    op.alter_column('jobs', 'mark_is_done_equipment_time',
                    server_default='false',
                    existing_type=sa.Boolean(),
                    existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove server_default from columns
    op.alter_column('jobs', 'mark_is_done_case',
                    server_default=None,
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
    op.alter_column('jobs', 'mark_is_done_witnesses',
                    server_default=None,
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
    op.alter_column('jobs', 'mark_is_done_attorneys',
                    server_default=None,
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
    op.alter_column('jobs', 'mark_is_done_billings',
                    server_default=None,
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
    op.alter_column('jobs', 'mark_is_done_equipment_time',
                    server_default=None,
                    existing_type=sa.Boolean(),
                    existing_nullable=True)
