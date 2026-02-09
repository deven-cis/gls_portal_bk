"""add_camera_captured_fields_to_attorneys_billings_equipment_time

Revision ID: add_camera_fields_001
Revises: 08650b7f076b
Create Date: 2026-02-09 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_camera_fields_001'
down_revision: Union[str, Sequence[str], None] = '08650b7f076b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add camera_captured_file_name and camera_captured_file_path to attorneys, billings, and equipment_time tables."""
    
    # Add columns to attorneys table
    op.add_column('attorneys', sa.Column('camera_captured_file_name', sa.Text(), nullable=True))
    op.add_column('attorneys', sa.Column('camera_captured_file_path', sa.Text(), nullable=True))
    
    # Add columns to billings table
    op.add_column('billings', sa.Column('camera_captured_file_name', sa.Text(), nullable=True))
    op.add_column('billings', sa.Column('camera_captured_file_path', sa.Text(), nullable=True))
    
    # Add columns to equipment_time table
    op.add_column('equipment_time', sa.Column('camera_captured_file_name', sa.Text(), nullable=True))
    op.add_column('equipment_time', sa.Column('camera_captured_file_path', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove camera_captured_file_name and camera_captured_file_path from attorneys, billings, and equipment_time tables."""
    
    # Remove columns from equipment_time table
    op.drop_column('equipment_time', 'camera_captured_file_path')
    op.drop_column('equipment_time', 'camera_captured_file_name')
    
    # Remove columns from billings table
    op.drop_column('billings', 'camera_captured_file_path')
    op.drop_column('billings', 'camera_captured_file_name')
    
    # Remove columns from attorneys table
    op.drop_column('attorneys', 'camera_captured_file_path')
    op.drop_column('attorneys', 'camera_captured_file_name')

