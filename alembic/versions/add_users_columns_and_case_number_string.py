"""add_users_columns_and_case_number_string

Revision ID: add_users_case_fields_001
Revises: add_camera_fields_001
Create Date: 2026-02-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_users_case_fields_001'
down_revision: Union[str, Sequence[str], None] = 'add_camera_fields_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add person_no and is_active columns to users table, and change case_number to String in cases table."""
    op.add_column('users', sa.Column('person_no', sa.Integer(), nullable=True, unique=True))
    op.create_index(op.f('ix_users_person_no'), 'users', ['person_no'], unique=True)
    
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))
    
    op.execute('ALTER TABLE cases ALTER COLUMN case_number TYPE VARCHAR(255) USING case_number::text')


def downgrade() -> None:
    """Remove person_no and is_active columns from users table, and revert case_number to Integer in cases table."""
    
    op.drop_index(op.f('ix_users_person_no'), table_name='users')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'person_no')
    
    op.execute('ALTER TABLE cases ALTER COLUMN case_number TYPE INTEGER USING case_number::integer')

