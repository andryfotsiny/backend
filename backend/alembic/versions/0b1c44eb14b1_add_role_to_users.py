"""add_role_to_users

Revision ID: 0b1c44eb14b1
Revises: 8310fa23de97
Create Date: 2026-02-09 16:31:53.951505

"""
from alembic import op
import sqlalchemy as sa


revision = '0b1c44eb14b1'
down_revision = '8310fa23de97'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ajouter colonne role avec default 'USER'
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='USER'))

    # Créer index
    op.create_index('idx_users_role', 'users', ['role'])

    # Supprimer server_default après migration
    op.alter_column('users', 'role', server_default=None)


def downgrade() -> None:
    # Supprimer index
    op.drop_index('idx_users_role', 'users')

    # Supprimer colonne
    op.drop_column('users', 'role')