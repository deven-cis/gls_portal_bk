"""add_mark_is_done_to_witnesses_attorneys_billings_equipment

Revision ID: b7a33a0e2d49
Revises: d14f5d4341f4
Create Date: 2025-12-19 14:33:15.429646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7a33a0e2d49'
down_revision: Union[str, Sequence[str], None] = 'd14f5d4341f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add mark_is_done to witnesses table
    op.add_column('witnesses', sa.Column('mark_is_done', sa.Boolean(), server_default='false', nullable=True))
    
    # Add mark_is_done to attorneys table
    op.add_column('attorneys', sa.Column('mark_is_done', sa.Boolean(), server_default='false', nullable=True))
    
    # Add mark_is_done to billings table
    op.add_column('billings', sa.Column('mark_is_done', sa.Boolean(), server_default='false', nullable=True))
    
    # Add mark_is_done to equipment_time table
    op.add_column('equipment_time', sa.Column('mark_is_done', sa.Boolean(), server_default='false', nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove mark_is_done from equipment_time table
    op.drop_column('equipment_time', 'mark_is_done')
    
    # Remove mark_is_done from billings table
    op.drop_column('billings', 'mark_is_done')
    
    # Remove mark_is_done from attorneys table
    op.drop_column('attorneys', 'mark_is_done')
    
    # Remove mark_is_done from witnesses table
    op.drop_column('witnesses', 'mark_is_done')
