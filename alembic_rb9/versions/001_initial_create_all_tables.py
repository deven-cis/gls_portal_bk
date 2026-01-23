"""initial_create_all_tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

Creates all tables for rb9_db:
- Users (with PascalCase columns)
- Cases (with PascalCase columns)
- Jobs (with PascalCase columns)
- Lists (lookup table)
- Timezones (lookup table)

All tables use PascalCase column naming convention.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for rb9_db with PascalCase columns."""
    
    # 1. Create Users table (no dependencies)
    op.create_table(
        'Users',
        sa.Column('UserNo', sa.Integer(), nullable=False),
        sa.Column('FullName', sa.String(80), nullable=True),
        sa.Column('FirstName', sa.String(30), nullable=True),
        sa.Column('MiddleName', sa.String(10), nullable=True),
        sa.Column('LastName', sa.String(30), nullable=True),
        sa.Column('LoginName', sa.String(80), nullable=True),
        sa.Column('LoginPassword', sa.Text(), nullable=True),
        sa.Column('Email', sa.String(80), nullable=True),
        sa.Column('LastModified', sa.DateTime(), nullable=True),
        sa.Column('LastModifiedBy', sa.Integer(), nullable=True),
        sa.Column('Entered', sa.DateTime(), nullable=True),
        sa.Column('EnteredBy', sa.Integer(), nullable=True),
        # RB9 tracking fields
        sa.Column('CreateAtRb', sa.DateTime(), nullable=True),
        sa.Column('UpdateAtRb', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('UserNo')
    )
    op.create_index(op.f('ix_Users_UserNo'), 'Users', ['UserNo'], unique=True)
    op.create_index(op.f('ix_Users_Email'), 'Users', ['Email'], unique=True)
    op.create_index(op.f('ix_Users_LoginName'), 'Users', ['LoginName'], unique=True)
    
    # 2. Create Lists table (needed by Cases for foreign keys)
    # ListNo is SERIAL (auto-increment) PRIMARY KEY
    op.create_table(
        'Lists',
        sa.Column('ListNo', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('ListValue', sa.String(40), nullable=True),
        sa.Column('LastModified', sa.DateTime(), nullable=True),
        sa.Column('LastModifiedBy', sa.Integer(), nullable=True),
        sa.Column('Entered', sa.DateTime(), nullable=True),
        sa.Column('EnteredBy', sa.Integer(), nullable=True),
        # RB9 tracking fields
        sa.Column('CreateAtRb', sa.DateTime(), nullable=True),
        sa.Column('UpdateAtRb', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('ListNo')
    )
    op.create_index(op.f('ix_Lists_ListNo'), 'Lists', ['ListNo'], unique=True)
    
    # 3. Create Cases table (depends on Lists)
    op.create_table(
        'Cases',
        sa.Column('CaseNo', sa.Integer(), nullable=False),
        sa.Column('CaseShortName', sa.String(80), nullable=True),
        sa.Column('CaseFullName', sa.String(1024), nullable=True),
        sa.Column('CaseType', sa.Integer(), nullable=True),  # Foreign key to Lists.ListNo
        sa.Column('Status', sa.Integer(), nullable=True),  # Foreign key to Lists.ListNo
        sa.Column('TrialDate', sa.Date(), nullable=True),
        sa.Column('LastModified', sa.DateTime(), nullable=True),
        sa.Column('LastModifiedBy', sa.Integer(), nullable=True),
        sa.Column('Entered', sa.DateTime(), nullable=True),
        sa.Column('EnteredBy', sa.Integer(), nullable=True),
        # RB9 tracking fields
        sa.Column('CreateAtRb', sa.DateTime(), nullable=True),
        sa.Column('UpdateAtRb', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('CaseNo'),
        sa.ForeignKeyConstraint(['CaseType'], ['Lists.ListNo'], name='fk_Cases_CaseType'),
        sa.ForeignKeyConstraint(['Status'], ['Lists.ListNo'], name='fk_Cases_Status')
    )
    op.create_index(op.f('ix_Cases_CaseNo'), 'Cases', ['CaseNo'], unique=True)
    op.create_index(op.f('ix_Cases_CaseType'), 'Cases', ['CaseType'], unique=False)
    op.create_index(op.f('ix_Cases_Status'), 'Cases', ['Status'], unique=False)
    
    # 4. Create Timezones table (needed by Jobs for foreign keys)
    op.create_table(
        'Timezones',
        sa.Column('TimezoneNo', sa.Integer(), nullable=False),
        sa.Column('TimezoneName', sa.String(80), nullable=True),
        sa.Column('TimezoneFullName', sa.String(128), nullable=True),
        sa.Column('StandardBias', sa.SmallInteger(), nullable=True),
        sa.Column('DaylightBias', sa.SmallInteger(), nullable=True),
        sa.Column('IsActive', sa.Boolean(), nullable=True),
        sa.Column('LastModified', sa.DateTime(), nullable=True),
        sa.Column('LastModifiedBy', sa.Integer(), nullable=True),
        # RB9 tracking fields
        sa.Column('CreateAtRb', sa.DateTime(), nullable=True),
        sa.Column('UpdateAtRb', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('TimezoneNo')
    )
    op.create_index(op.f('ix_Timezones_TimezoneNo'), 'Timezones', ['TimezoneNo'], unique=True)
    
    # 5. Create Jobs table (depends on Cases)
    op.create_table(
        'Jobs',
        sa.Column('JobNo', sa.Integer(), nullable=False),
        sa.Column('JobDate', sa.Date(), nullable=True),
        sa.Column('StartTime', sa.Time(), nullable=True),
        sa.Column('EndTime', sa.Time(), nullable=True),
        sa.Column('TimezoneNo', sa.Integer(), nullable=True),
        sa.Column('CaseNo', sa.Integer(), nullable=True),  
        sa.Column('Status', sa.Integer(), nullable=True),  # Foreign key to Lists.ListNo
        sa.Column('JobType', sa.Integer(), nullable=True),
        sa.Column('ScheduledByEmail', sa.String(80), nullable=True),
        sa.Column('JobLocName', sa.String(80), nullable=True),
        sa.Column('JobLocAddress', sa.String(128), nullable=True),
        sa.Column('JobLocCity', sa.String(40), nullable=True),
        sa.Column('JobLocState', sa.String(10), nullable=True),
        sa.Column('JobLocZip', sa.String(10), nullable=True),
        sa.Column('SchedulingNotesHtml', sa.Text(), nullable=True),
        sa.Column('ZoomMeetingId', sa.String(255), nullable=True),
        sa.Column('ConfirmationNotesHtml', sa.Text(), nullable=True),
        sa.Column('LastModified', sa.DateTime(), nullable=True),
        sa.Column('LastModifiedBy', sa.Integer(), nullable=True),
        sa.Column('Entered', sa.DateTime(), nullable=True),
        sa.Column('EnteredBy', sa.Integer(), nullable=True),
        # RB9 tracking fields
        sa.Column('CreateAtRb', sa.DateTime(), nullable=True),
        sa.Column('UpdateAtRb', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('JobNo'),
        sa.ForeignKeyConstraint(['CaseNo'], ['Cases.CaseNo'], name='fk_Jobs_CaseNo'),
        sa.ForeignKeyConstraint(['TimezoneNo'], ['Timezones.TimezoneNo'], name='fk_Jobs_TimezoneNo')
    )
    op.create_index(op.f('ix_Jobs_JobNo'), 'Jobs', ['JobNo'], unique=True)
    op.create_index(op.f('ix_Jobs_CaseNo'), 'Jobs', ['CaseNo'], unique=False)
    op.create_index(op.f('ix_Jobs_TimezoneNo'), 'Jobs', ['TimezoneNo'], unique=False)


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table('Jobs')
    op.drop_table('Timezones')
    op.drop_table('Cases')
    op.drop_table('Lists')
    op.drop_table('Users')

