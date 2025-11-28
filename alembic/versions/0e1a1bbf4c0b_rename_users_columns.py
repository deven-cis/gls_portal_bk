"""rename users columns

Revision ID: 0e1a1bbf4c0b
Revises: 53db67916bac
Create Date: 2025-11-27 15:37:16.098337

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e1a1bbf4c0b'
down_revision: Union[str, Sequence[str], None] = '53db67916bac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f('ix_users_Email'), table_name='users')
    op.drop_index(op.f('ix_users_LoginName'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')

    rename_map = (
        ('FullName', 'full_name'),
        ('Email', 'email'),
        ('LoginName', 'login_name'),
        ('LoginPassword', 'login_password'),
        ('Profile_Image', 'profile_image_url'),
        ('Entered', 'entered_at'),
        ('LastModified', 'last_modified_at'),
        ('EnteredBy', 'entered_by'),
        ('LastModifiedBy', 'last_modified_by'),
    )

    with op.batch_alter_table('users', schema=None) as batch_op:
        for old_name, new_name in rename_map:
            batch_op.alter_column(old_name, new_column_name=new_name)

        batch_op.alter_column(
            'entered_by',
            existing_type=sa.Integer(),
            nullable=False,
            server_default='0',
        )
        batch_op.alter_column(
            'last_modified_by',
            existing_type=sa.Integer(),
            nullable=False,
            server_default='0',
        )
        batch_op.add_column(
            sa.Column(
                'require_password_change',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_login_name'), 'users', ['login_name'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    op.alter_column('users', 'entered_by', server_default=None)
    op.alter_column('users', 'last_modified_by', server_default=None)
    op.alter_column('users', 'require_password_change', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_login_name'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('require_password_change')
        batch_op.alter_column(
            'last_modified_by',
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column(
            'entered_by',
            existing_type=sa.Integer(),
            nullable=True,
        )

        rename_map = (
            ('last_modified_by', 'LastModifiedBy'),
            ('entered_by', 'EnteredBy'),
            ('last_modified_at', 'LastModified'),
            ('entered_at', 'Entered'),
            ('profile_image_url', 'Profile_Image'),
            ('login_password', 'LoginPassword'),
            ('login_name', 'LoginName'),
            ('email', 'Email'),
            ('full_name', 'FullName'),
        )

        for old_name, new_name in rename_map:
            batch_op.alter_column(old_name, new_column_name=new_name)

    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_LoginName'), 'users', ['LoginName'], unique=True)
    op.create_index(op.f('ix_users_Email'), 'users', ['Email'], unique=True)
