"""add_video_merge_fields_to_witnesses_and_witness_videos

Revision ID: da0efb110766
Revises: 20260305_job_assign_resources
Create Date: 2026-03-19 11:51:56.136274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'da0efb110766'
down_revision: Union[str, Sequence[str], None] = '20260305_job_assign_resources'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── WitnessVideos — 3 new columns ──────────────────────────────
    op.add_column('witness_videos', sa.Column('file_size', sa.BigInteger(), nullable=True))
    op.add_column('witness_videos', sa.Column('duration_seconds', sa.Numeric(10, 2), nullable=True))
    op.add_column('witness_videos', sa.Column('timecode', sa.Text(), nullable=True))

    # ── Witnesses — 8 new columns ───────────────────────────────────
    op.add_column('witnesses', sa.Column('merged_video_path', sa.Text(), nullable=True))
    op.add_column('witnesses', sa.Column('merged_video_name', sa.Text(), nullable=True))
    op.add_column('witnesses', sa.Column('merged_video_size', sa.BigInteger(), nullable=True))
    op.add_column('witnesses', sa.Column('merged_duration', sa.Numeric(10, 2), nullable=True))
    op.add_column('witnesses', sa.Column('merge_status', sa.String(50), nullable=True))
    op.add_column('witnesses', sa.Column('merge_error', sa.Text(), nullable=True))
    op.add_column('witnesses', sa.Column('merge_requested_at', sa.DateTime(), nullable=True))
    op.add_column('witnesses', sa.Column('merge_completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # ── WitnessVideos ───────────────────────────────────────────────
    op.drop_column('witness_videos', 'file_size')
    op.drop_column('witness_videos', 'duration_seconds')
    op.drop_column('witness_videos', 'timecode')

    # ── Witnesses ───────────────────────────────────────────────────
    op.drop_column('witnesses', 'merged_video_path')
    op.drop_column('witnesses', 'merged_video_name')
    op.drop_column('witnesses', 'merged_video_size')
    op.drop_column('witnesses', 'merged_duration')
    op.drop_column('witnesses', 'merge_status')
    op.drop_column('witnesses', 'merge_error')
    op.drop_column('witnesses', 'merge_requested_at')
    op.drop_column('witnesses', 'merge_completed_at')