"""Add error_message column to analysis_runs table

Revision ID: b7a891c2d3e4
Revises: 65b0b341ba01
Create Date: 2026-10-05 23:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7a891c2d3e4'
down_revision = '65b0b341ba01'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('analysis_runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('analysis_runs', schema=None) as batch_op:
        batch_op.drop_column('error_message')
