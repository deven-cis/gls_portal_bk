"""
Update job_assignments table to use resources and jobs_tasks associations
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260305_job_assign_resources'
down_revision = '20260305_add_jobs_tasks_table'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('job_assignments') as batch_op:
        batch_op.drop_constraint('job_assignments_assigner_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('job_assignments_assignee_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('job_assignments_job_no_fkey', type_='foreignkey')
        batch_op.drop_column('job_no')
        batch_op.add_column(sa.Column('job_task_no', sa.Integer, nullable=False))
        batch_op.create_foreign_key('job_assignments_assigner_id_fkey', 'resources', ['assigner_id'], ['rsrc_no'])
        batch_op.create_foreign_key('job_assignments_assignee_id_fkey', 'resources', ['assignee_id'], ['rsrc_no'])
        batch_op.create_foreign_key('job_assignments_job_task_no_fkey', 'jobs_tasks', ['job_task_no'], ['task_no'])

def downgrade():
    with op.batch_alter_table('job_assignments') as batch_op:
        batch_op.drop_constraint('job_assignments_assigner_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('job_assignments_assignee_id_fkey', type_='foreignkey')
        batch_op.drop_constraint('job_assignments_job_task_no_fkey', type_='foreignkey')
        batch_op.drop_column('job_task_no')
        batch_op.add_column(sa.Column('job_no', sa.Integer, nullable=False))
        batch_op.create_foreign_key('job_assignments_assigner_id_fkey', 'users', ['assigner_id'], ['id'])
        batch_op.create_foreign_key('job_assignments_assignee_id_fkey', 'users', ['assignee_id'], ['id'])
        batch_op.create_foreign_key('job_assignments_job_no_fkey', 'jobs', ['job_no'], ['job_no'])
