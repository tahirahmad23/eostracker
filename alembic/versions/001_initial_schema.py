"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2026-01-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial tables."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('tier', sa.Enum('free', 'pro', name='usertier'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    
    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendor', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=255), nullable=False),
        sa.Column('device_type', sa.String(length=100), nullable=False),
        sa.Column('eos_date', sa.Date(), nullable=False),
        sa.Column('eol_date', sa.Date(), nullable=True),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_devices_device_type'), 'devices', ['device_type'], unique=False)
    op.create_index(op.f('ix_devices_eos_date'), 'devices', ['eos_date'], unique=False)
    op.create_index(op.f('ix_devices_id'), 'devices', ['id'], unique=False)
    op.create_index(op.f('ix_devices_slug'), 'devices', ['slug'], unique=True)
    op.create_index(op.f('ix_devices_vendor'), 'devices', ['vendor'], unique=False)
    op.create_index('idx_vendor_model', 'devices', ['vendor', 'model'], unique=False)
    op.create_index('idx_vendor_type', 'devices', ['vendor', 'device_type'], unique=False)
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('paystack_subscription_code', sa.String(length=255), nullable=False),
        sa.Column('paystack_customer_code', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('active', 'canceled', 'expired', name='subscriptionstatus'), nullable=False),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('paystack_subscription_code'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    
    # Create tracked_devices table
    op.create_table(
        'tracked_devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('custom_name', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tracked_devices_device_id'), 'tracked_devices', ['device_id'], unique=False)
    op.create_index(op.f('ix_tracked_devices_id'), 'tracked_devices', ['id'], unique=False)
    op.create_index(op.f('ix_tracked_devices_user_id'), 'tracked_devices', ['user_id'], unique=False)
    op.create_index('idx_user_device', 'tracked_devices', ['user_id', 'device_id'], unique=True)
    
    # Create alert_history table
    op.create_table(
        'alert_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tracked_device_id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.Enum('365', '180', '90', '30', name='alerttype'), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('email_status', sa.Enum('sent', 'failed', name='emailstatus'), nullable=False),
        sa.ForeignKeyConstraint(['tracked_device_id'], ['tracked_devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_history_id'), 'alert_history', ['id'], unique=False)
    op.create_index(op.f('ix_alert_history_tracked_device_id'), 'alert_history', ['tracked_device_id'], unique=False)
    op.create_index(op.f('ix_alert_history_user_id'), 'alert_history', ['user_id'], unique=False)
    op.create_index('idx_alert_unique', 'alert_history', ['user_id', 'tracked_device_id', 'alert_type'], unique=True)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index('idx_alert_unique', table_name='alert_history')
    op.drop_index(op.f('ix_alert_history_user_id'), table_name='alert_history')
    op.drop_index(op.f('ix_alert_history_tracked_device_id'), table_name='alert_history')
    op.drop_index(op.f('ix_alert_history_id'), table_name='alert_history')
    op.drop_table('alert_history')
    
    op.drop_index('idx_user_device', table_name='tracked_devices')
    op.drop_index(op.f('ix_tracked_devices_user_id'), table_name='tracked_devices')
    op.drop_index(op.f('ix_tracked_devices_id'), table_name='tracked_devices')
    op.drop_index(op.f('ix_tracked_devices_device_id'), table_name='tracked_devices')
    op.drop_table('tracked_devices')
    
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    
    op.drop_index('idx_vendor_type', table_name='devices')
    op.drop_index('idx_vendor_model', table_name='devices')
    op.drop_index(op.f('ix_devices_vendor'), table_name='devices')
    op.drop_index(op.f('ix_devices_slug'), table_name='devices')
    op.drop_index(op.f('ix_devices_id'), table_name='devices')
    op.drop_index(op.f('ix_devices_eos_date'), table_name='devices')
    op.drop_index(op.f('ix_devices_device_type'), table_name='devices')
    op.drop_table('devices')
    
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS emailstatus')
    op.execute('DROP TYPE IF EXISTS alerttype')
    op.execute('DROP TYPE IF EXISTS subscriptionstatus')
    op.execute('DROP TYPE IF EXISTS usertier')
