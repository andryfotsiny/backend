"""add detection_log indexes

Revision ID: a1b2c3d4e5f6
Revises: dd01025878b5
Create Date: 2026-06-01 00:00:00.000000

"""
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'dd01025878b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_detection_logs_user_type",
        "detection_logs",
        ["user_id", "detection_type"],
        unique=False,
    )
    op.create_index(
        "ix_detection_logs_fraud_timestamp",
        "detection_logs",
        ["is_fraud", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_detection_logs_method",
        "detection_logs",
        ["method_used"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_detection_logs_method", table_name="detection_logs")
    op.drop_index("ix_detection_logs_fraud_timestamp", table_name="detection_logs")
    op.drop_index("ix_detection_logs_user_type", table_name="detection_logs")
