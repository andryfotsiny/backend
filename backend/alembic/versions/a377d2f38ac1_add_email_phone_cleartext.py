"""add_email_phone_cleartext

Revision ID: a377d2f38ac1
Revises: 0b1c44eb14b1
Create Date: 2026-02-12 09:01:08.856073

"""
from alembic import op
import sqlalchemy as sa

revision = 'a377d2f38ac1'
down_revision = '0b1c44eb14b1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter email et phone en clair
    # (email_hash et phone_hash existent déjà depuis 001_initial_migration)
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))

    # Index unique sur email
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")

    # Ajouter FK detection_logs -> users si pas déjà présente
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_type = 'FOREIGN KEY'
                AND table_name = 'detection_logs'
                AND constraint_name LIKE '%user_id%'
            ) THEN
                ALTER TABLE detection_logs
                ADD CONSTRAINT fk_detection_logs_user_id
                FOREIGN KEY (user_id) REFERENCES users(user_id);
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.drop_column('users', 'phone')
    op.drop_column('users', 'email')