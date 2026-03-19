"""add_uploaded_videos_table

Revision ID: 20260319_uploaded_videos
Revises: da0efb110766
Create Date: 2026-03-19 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260319_uploaded_videos'
down_revision: Union[str, Sequence[str], None] = 'da0efb110766'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'uploaded_videos',
        sa.Column('upload_id', sa.String(length=64), nullable=False),
        sa.Column('original_file_name', sa.Text(), nullable=False),
        sa.Column('stored_file_name', sa.Text(), nullable=True),
        sa.Column('content_type', sa.String(length=255), nullable=True),
        sa.Column('file_ext', sa.String(length=20), nullable=False),
        sa.Column('temp_file_path', sa.Text(), nullable=True),
        sa.Column('final_file_path', sa.Text(), nullable=True),
        sa.Column('expected_file_size', sa.BigInteger(), nullable=True),
        sa.Column('bytes_received', sa.BigInteger(), nullable=True),
        sa.Column('total_chunks', sa.Integer(), nullable=True),
        sa.Column('received_chunks', sa.Integer(), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('duration_seconds', sa.Numeric(10, 2), nullable=True),
        sa.Column('timecode', sa.Text(), nullable=True),
        sa.Column('format_name', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('attached_at', sa.DateTime(), nullable=True),
        sa.Column('witness_video_id', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entered_at', sa.DateTime(), nullable=True),
        sa.Column('entered_by', sa.Integer(), nullable=False),
        sa.Column('last_modified_at', sa.DateTime(), nullable=True),
        sa.Column('last_modified_by', sa.Integer(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=True),
        sa.ForeignKeyConstraint(['witness_video_id'], ['witness_videos.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_uploaded_videos_id'), 'uploaded_videos', ['id'], unique=False)
    op.create_index(op.f('ix_uploaded_videos_upload_id'), 'uploaded_videos', ['upload_id'], unique=True)
    op.create_index(op.f('ix_uploaded_videos_expires_at'), 'uploaded_videos', ['expires_at'], unique=False)
    op.create_index(op.f('ix_uploaded_videos_witness_video_id'), 'uploaded_videos', ['witness_video_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_uploaded_videos_witness_video_id'), table_name='uploaded_videos')
    op.drop_index(op.f('ix_uploaded_videos_expires_at'), table_name='uploaded_videos')
    op.drop_index(op.f('ix_uploaded_videos_upload_id'), table_name='uploaded_videos')
    op.drop_index(op.f('ix_uploaded_videos_id'), table_name='uploaded_videos')
    op.drop_table('uploaded_videos')
