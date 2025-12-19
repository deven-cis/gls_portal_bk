"""add_session_tracking_and_progress_fields

Revision ID: d14f5d4341f4
Revises: 5b48f96a1c39
Create Date: 2025-12-19 14:19:42.978561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd14f5d4341f4'
down_revision: Union[str, Sequence[str], None] = '5b48f96a1c39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add session tracking fields to jobs table
    op.add_column('jobs', sa.Column('actual_session_start_time', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('actual_session_end_time', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('session_duration', sa.String(length=8), nullable=True))  # HH:MM:SS format
    op.add_column('jobs', sa.Column('session_completed', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('jobs', sa.Column('mark_is_done', sa.Boolean(), server_default='false', nullable=True))
    
    # Add video tracking fields to jobs (optional)
    op.add_column('jobs', sa.Column('video_upload_deadline', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('expected_video_count', sa.Integer(), nullable=True))
    
    # Add mark_is_done to cases table
    op.add_column('cases', sa.Column('mark_is_done', sa.Boolean(), server_default='false', nullable=True))
    
    # Optional: Add case progress fields
    op.add_column('cases', sa.Column('progress_percentage', sa.Float(), nullable=True))
    op.add_column('cases', sa.Column('total_jobs', sa.Integer(), nullable=True))
    op.add_column('cases', sa.Column('completed_jobs', sa.Integer(), nullable=True))
    op.add_column('cases', sa.Column('case_status', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove case progress fields
    op.drop_column('cases', 'case_status')
    op.drop_column('cases', 'completed_jobs')
    op.drop_column('cases', 'total_jobs')
    op.drop_column('cases', 'progress_percentage')
    op.drop_column('cases', 'mark_is_done')
    
    # Remove job fields
    op.drop_column('jobs', 'expected_video_count')
    op.drop_column('jobs', 'video_upload_deadline')
    op.drop_column('jobs', 'mark_is_done')
    op.drop_column('jobs', 'session_completed')
    op.drop_column('jobs', 'session_duration')
    op.drop_column('jobs', 'actual_session_end_time')
    op.drop_column('jobs', 'actual_session_start_time')
