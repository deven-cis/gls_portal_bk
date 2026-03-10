"""
Add jobs_tasks table and update resources relationship
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260305_add_jobs_tasks_table'
down_revision = 'add_users_case_fields_001'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'resources',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('rsrc_no', sa.Integer, unique=True, index=True, nullable=False),
        sa.Column('person_no', sa.Integer, index=True, nullable=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('middle_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('main_phone', sa.String(50), nullable=True),
        sa.Column('alt_phone', sa.String(50), nullable=True),
        sa.Column('fax', sa.Text, nullable=True),
        sa.Column('mobile', sa.String(50), nullable=True),
        sa.Column('sms_provider_no', sa.Integer, nullable=True),
        sa.Column('login_name', sa.String(150), index=True, nullable=True),
        sa.Column('login_password', sa.LargeBinary, nullable=True),
        sa.Column('email', sa.String(255), index=True, nullable=True),
        sa.Column('require_password_change', sa.Boolean, default=False, server_default='false'),
        sa.Column('profile_image_url', sa.String(1024), nullable=True),
        sa.Column('is_active', sa.Boolean, default=False, server_default='false'),
        sa.Column('is_locked', sa.Boolean, default=False, server_default='false'),
        sa.Column('try_login_cnt', sa.Integer, default=0, server_default='0'),
        sa.Column('last_pwd_changed', sa.DateTime, nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('salutation', sa.String(1024), nullable=True),
        sa.Column('address', sa.String(1024), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(50), nullable=True),
        sa.Column('zip', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('directions', sa.Text, nullable=True),
        sa.Column('rsrc_type', sa.String(1024), nullable=True),
        sa.Column('warning', sa.Text, nullable=True),
        sa.Column('start_date', sa.Date, nullable=True),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('is_no_pay', sa.Boolean, default=False, server_default='false'),
        sa.Column('priority_level', sa.String(1024), nullable=True),
        sa.Column('pay_rate_group', sa.String(1024), nullable=True),
        sa.Column('pay_group', sa.String(1024), nullable=True),
        sa.Column('commission_rate_cover', sa.Numeric(10, 4), nullable=True),
        sa.Column('commission_rate_no_cover', sa.Numeric(10, 4), nullable=True),
        sa.Column('is_self_scope', sa.Boolean, default=False, server_default='false'),
        sa.Column('recurring_amt', sa.Numeric(12, 2), nullable=True),
        sa.Column('recurring_from', sa.Date, nullable=True),
        sa.Column('recurring_to', sa.Date, nullable=True),
        sa.Column('is_direct_deposit', sa.Boolean, default=False, server_default='false'),
        sa.Column('work_schedule_sun', sa.String(1024), nullable=True),
        sa.Column('work_schedule_mon', sa.String(1024), nullable=True),
        sa.Column('work_schedule_tue', sa.String(1024), nullable=True),
        sa.Column('work_schedule_wed', sa.String(1024), nullable=True),
        sa.Column('work_schedule_thu', sa.String(1024), nullable=True),
        sa.Column('work_schedule_fri', sa.String(1024), nullable=True),
        sa.Column('work_schedule_sat', sa.String(1024), nullable=True),
        sa.Column('entered_at', sa.DateTime, nullable=True),
        sa.Column('entered_by', sa.Integer, nullable=True),
        sa.Column('last_modified_at', sa.DateTime, nullable=True),
        sa.Column('last_modified_by', sa.Integer, nullable=True),
        sa.Column('is_archived', sa.Boolean, nullable=True, server_default='false'),
    )

    op.create_table(
        'jobs_tasks',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('task_no', sa.Integer, unique=True, index=True, nullable=False),
        sa.Column('job_no', sa.Integer, sa.ForeignKey('jobs.job_no', ondelete='CASCADE'), nullable=False),
        sa.Column('rsrc_no', sa.Integer, sa.ForeignKey('resources.rsrc_no'), nullable=True),
        sa.Column('task_list_note', sa.String(1024), nullable=True),
        sa.Column('notified_date', sa.DateTime, nullable=True),
        sa.Column('order_date', sa.Date, nullable=True),
        sa.Column('due_date', sa.Date, nullable=True),
        sa.Column('cancel_date', sa.DateTime, nullable=True),
        sa.Column('acknowledged_date', sa.DateTime, nullable=True),
        sa.Column('estimated_delivery_date', sa.Date, nullable=True),
        sa.Column('turn_in_date', sa.DateTime, nullable=True),
        sa.Column('cancel_by', sa.Integer, nullable=True),
        sa.Column('estimated_pages', sa.Integer, nullable=True),
        sa.Column('task_notes', sa.Text, nullable=True),
        sa.Column('rsrc_notes', sa.Text, nullable=True),
        sa.Column('entered_at', sa.DateTime, nullable=True),
        sa.Column('entered_by', sa.Integer, nullable=True),
        sa.Column('last_modified_at', sa.DateTime, nullable=True),
        sa.Column('last_modified_by', sa.Integer, nullable=True),
        sa.Column('is_archived', sa.Boolean, nullable=True, server_default='false'),
    )

def downgrade():
    op.drop_table('jobs_tasks')
    op.drop_table('resources')
