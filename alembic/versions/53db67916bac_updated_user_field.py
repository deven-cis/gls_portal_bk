"""updated user field

Revision ID: 53db67916bac
Revises: 8f7a219c2ff1
Create Date: 2025-11-24 20:37:31.006226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53db67916bac'
down_revision: Union[str, Sequence[str], None] = '8f7a219c2ff1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'users',
        'LoginPassword',
        type_=sa.LargeBinary(),
        existing_type=sa.VARCHAR(),
        nullable=True,
        postgresql_using='"LoginPassword"::bytea'
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.alter_column(
        'users',
        'LoginPassword',
        type_=sa.VARCHAR(),
        existing_type=sa.LargeBinary(),
        nullable=False,
        postgresql_using='"LoginPassword"::varchar'
    )
    # ### end Alembic commands ###
