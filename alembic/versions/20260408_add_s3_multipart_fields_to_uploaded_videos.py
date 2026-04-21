"""add_s3_multipart_fields_to_uploaded_videos

Revision ID: 20260408_s3_multipart
Revises: 20260319_uploaded_videos
Create Date: 2026-04-08 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260408_s3_multipart"
down_revision: Union[str, Sequence[str], None] = "20260319_uploaded_videos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("uploaded_videos", sa.Column("multipart_upload_id", sa.Text(), nullable=True))
    op.add_column("uploaded_videos", sa.Column("multipart_object_key", sa.Text(), nullable=True))
    op.add_column("uploaded_videos", sa.Column("upload_strategy", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("uploaded_videos", "upload_strategy")
    op.drop_column("uploaded_videos", "multipart_object_key")
    op.drop_column("uploaded_videos", "multipart_upload_id")
