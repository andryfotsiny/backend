"""add meta_data to detection_logs

Revision ID: b1c2d3e4f5a6
Revises: a377d2f38ac1
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b1c2d3e4f5a6'
down_revision = 'a377d2f38ac1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'detection_logs',
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('detection_logs', 'meta_data')