"""initial migration

Revision ID: 001
Revises: 
Create Date: 2025-01-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_hash', sa.String(length=64), nullable=False),
        sa.Column('phone_hash', sa.String(length=64), nullable=True),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_active', sa.DateTime(), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('device_tokens', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('report_count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index(op.f('ix_users_email_hash'), 'users', ['email_hash'], unique=True)
    op.create_index(op.f('ix_users_phone_hash'), 'users', ['phone_hash'], unique=True)

    op.create_table('fraudulent_numbers',
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('country_code', sa.String(length=3), nullable=False),
        sa.Column('fraud_type', sa.Enum('SPAM', 'SCAM', 'ROBOCALL', 'PHISHING', 'SPOOFING', name='fraudtype'), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('report_count', sa.Integer(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=True),
        sa.Column('first_reported', sa.DateTime(), nullable=True),
        sa.Column('last_reported', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('phone_number')
    )
    op.create_index(op.f('ix_fraudulent_numbers_phone_number'), 'fraudulent_numbers', ['phone_number'], unique=False)
    op.create_index(op.f('ix_fraudulent_numbers_country_code'), 'fraudulent_numbers', ['country_code'], unique=False)

    op.create_table('fraudulent_sms_patterns',
        sa.Column('pattern_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('regex_pattern', sa.String(), nullable=True),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('fraud_category', sa.String(length=50), nullable=True),
        sa.Column('language', sa.String(length=5), nullable=True),
        sa.Column('severity', sa.Integer(), nullable=True),
        sa.Column('detection_count', sa.Integer(), nullable=True),
        sa.Column('false_positive_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('pattern_id')
    )
    op.create_index(op.f('ix_fraudulent_sms_patterns_fraud_category'), 'fraudulent_sms_patterns', ['fraud_category'], unique=False)

    op.create_table('fraudulent_domains',
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('phishing_type', sa.String(length=50), nullable=True),
        sa.Column('first_seen', sa.DateTime(), nullable=True),
        sa.Column('blocked_count', sa.Integer(), nullable=True),
        sa.Column('spf_valid', sa.Boolean(), nullable=True),
        sa.Column('dkim_valid', sa.Boolean(), nullable=True),
        sa.Column('dmarc_policy', sa.String(length=20), nullable=True),
        sa.Column('reputation_score', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('domain')
    )
    op.create_index(op.f('ix_fraudulent_domains_domain'), 'fraudulent_domains', ['domain'], unique=False)

    op.create_table('ml_model_versions',
        sa.Column('version_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('training_date', sa.DateTime(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=False),
        sa.Column('precision', sa.Float(), nullable=False),
        sa.Column('recall', sa.Float(), nullable=False),
        sa.Column('f1_score', sa.Float(), nullable=False),
        sa.Column('training_samples', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('model_path', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('version_id')
    )

    op.create_table('user_reports',
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_type', sa.Enum('CALL', 'SMS', 'EMAIL', name='reporttype'), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('verification_status', sa.Enum('PENDING', 'VERIFIED', 'REJECTED', name='verificationstatus'), nullable=True),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('report_id')
    )
    op.create_index(op.f('ix_user_reports_timestamp'), 'user_reports', ['timestamp'], unique=False)

    op.create_table('detection_logs',
        sa.Column('log_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('detection_type', sa.String(length=20), nullable=False),
        sa.Column('is_fraud', sa.Boolean(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('method_used', sa.String(length=20), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('model_version', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('log_id')
    )
    op.create_index(op.f('ix_detection_logs_detection_type'), 'detection_logs', ['detection_type'], unique=False)
    op.create_index(op.f('ix_detection_logs_timestamp'), 'detection_logs', ['timestamp'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_detection_logs_timestamp'), table_name='detection_logs')
    op.drop_index(op.f('ix_detection_logs_detection_type'), table_name='detection_logs')
    op.drop_table('detection_logs')
    op.drop_index(op.f('ix_user_reports_timestamp'), table_name='user_reports')
    op.drop_table('user_reports')
    op.drop_table('ml_model_versions')
    op.drop_index(op.f('ix_fraudulent_domains_domain'), table_name='fraudulent_domains')
    op.drop_table('fraudulent_domains')
    op.drop_index(op.f('ix_fraudulent_sms_patterns_fraud_category'), table_name='fraudulent_sms_patterns')
    op.drop_table('fraudulent_sms_patterns')
    op.drop_index(op.f('ix_fraudulent_numbers_country_code'), table_name='fraudulent_numbers')
    op.drop_index(op.f('ix_fraudulent_numbers_phone_number'), table_name='fraudulent_numbers')
    op.drop_table('fraudulent_numbers')
    op.drop_index(op.f('ix_users_phone_hash'), table_name='users')
    op.drop_index(op.f('ix_users_email_hash'), table_name='users')
    op.drop_table('users')
