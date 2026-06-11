"""Initial migration — aligned with ORM models

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('role', sa.Enum('CLIENT', 'DRIVER', 'ADMIN', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('google_id', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('email', name='uq_users_email'),
        sa.UniqueConstraint('google_id', name='uq_users_google_id'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_role', 'users', ['role'])

    # ── drivers ───────────────────────────────────────────
    op.create_table(
        'drivers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('license_number', sa.String(100), nullable=False),
        sa.Column('vehicle_type', sa.String(100), nullable=False),
        sa.Column('vehicle_number', sa.String(50), nullable=False),
        sa.Column('vehicle_model', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('ONLINE', 'OFFLINE', 'BUSY', 'ON_DELIVERY', name='driverstatus'), nullable=False, server_default='OFFLINE'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_suspended', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('documents', postgresql.JSONB(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('total_deliveries', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_lat', sa.Float(), nullable=True),
        sa.Column('current_lng', sa.Float(), nullable=True),
        sa.Column('last_location_update', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', name='uq_drivers_user_id'),
        sa.UniqueConstraint('license_number', name='uq_drivers_license'),
        sa.UniqueConstraint('vehicle_number', name='uq_drivers_vehicle_number'),
    )
    op.create_index('ix_drivers_id', 'drivers', ['id'])
    op.create_index('ix_drivers_status', 'drivers', ['status'])

    # ── offers ────────────────────────────────────────────
    op.create_table(
        'offers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('offer_type', sa.Enum('PERCENTAGE', 'FLAT', 'FREE_DELIVERY', name='offertype'), nullable=False),
        sa.Column('discount_value', sa.Float(), nullable=False),
        sa.Column('min_order_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('max_discount', sa.Float(), nullable=True),
        sa.Column('usage_limit', sa.Integer(), nullable=True),
        sa.Column('used_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('code', name='uq_offers_code'),
    )
    op.create_index('ix_offers_id', 'offers', ['id'])
    op.create_index('ix_offers_code', 'offers', ['code'])

    # ── deliveries ────────────────────────────────────────
    op.create_table(
        'deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('drivers.id'), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED', name='deliverystatus'), nullable=False, server_default='PENDING'),
        sa.Column('pickup_address', sa.Text(), nullable=False),
        sa.Column('pickup_lat', sa.Float(), nullable=False),
        sa.Column('pickup_lng', sa.Float(), nullable=False),
        sa.Column('pickup_contact_name', sa.String(255), nullable=True),
        sa.Column('pickup_contact_phone', sa.String(20), nullable=True),
        sa.Column('dropoff_address', sa.Text(), nullable=False),
        sa.Column('dropoff_lat', sa.Float(), nullable=False),
        sa.Column('dropoff_lng', sa.Float(), nullable=False),
        sa.Column('dropoff_contact_name', sa.String(255), nullable=True),
        sa.Column('dropoff_contact_phone', sa.String(20), nullable=True),
        sa.Column('parcel_description', sa.Text(), nullable=True),
        sa.Column('parcel_weight', sa.Float(), nullable=True),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('base_fare', sa.Float(), nullable=True),
        sa.Column('weather_multiplier', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('surge_multiplier', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('discount_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_fare', sa.Float(), nullable=True),
        sa.Column('weather_condition', sa.Enum('NORMAL', 'LIGHT_RAIN', 'MODERATE_RAIN', 'HEAVY_RAIN', name='weathercondition'), nullable=True, server_default='NORMAL'),
        sa.Column('coupon_code', sa.String(50), nullable=True),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('offers.id'), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('picked_up_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('special_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_deliveries_id', 'deliveries', ['id'])
    op.create_index('ix_deliveries_status', 'deliveries', ['status'])
    op.create_index('ix_deliveries_client_id', 'deliveries', ['client_id'])

    # ── locations ─────────────────────────────────────────
    op.create_table(
        'locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('drivers.id'), nullable=False),
        sa.Column('delivery_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('deliveries.id'), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('heading', sa.Float(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_locations_id', 'locations', ['id'])
    op.create_index('ix_locations_driver_timestamp', 'locations', ['driver_id', 'timestamp'])

    # ── payments ──────────────────────────────────────────
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('delivery_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('deliveries.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('status', sa.Enum('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED', name='paymentstatus'), nullable=False, server_default='PENDING'),
        sa.Column('razorpay_order_id', sa.String(255), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(255), nullable=True),
        sa.Column('razorpay_signature', sa.String(512), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('refund_id', sa.String(255), nullable=True),
        sa.Column('refunded_at', sa.DateTime(), nullable=True),
        sa.Column('invoice_url', sa.String(512), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('delivery_id', name='uq_payments_delivery_id'),
    )
    op.create_index('ix_payments_id', 'payments', ['id'])
    op.create_index('ix_payment_status', 'payments', ['status'])

    # ── offer_usage ───────────────────────────────────────
    op.create_table(
        'offer_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('offers.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('delivery_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('deliveries.id'), nullable=True),
        sa.Column('discount_applied', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_offer_usage_id', 'offer_usage', ['id'])

    # ── notifications ─────────────────────────────────────
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('channel', sa.Enum('IN_APP', 'EMAIL', 'REAL_TIME', name='notificationchannel'), nullable=False, server_default='IN_APP'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('event_type', sa.String(100), nullable=True),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_notifications_id', 'notifications', ['id'])
    op.create_index('ix_notification_user_read', 'notifications', ['user_id', 'is_read'])

    # ── audit_logs ────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_user_action', 'audit_logs', ['user_id', 'action'])

    # ── driver_ratings ────────────────────────────────────
    op.create_table(
        'driver_ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('drivers.id'), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('delivery_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('deliveries.id'), nullable=False),
        sa.Column('rating', sa.Float(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('delivery_id', 'client_id', name='uq_rating_delivery_client'),
    )
    op.create_index('ix_driver_ratings_id', 'driver_ratings', ['id'])

    # ── refresh_tokens ────────────────────────────────────
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('token', name='uq_refresh_tokens_token'),
    )
    op.create_index('ix_refresh_tokens_id', 'refresh_tokens', ['id'])
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token'])


def downgrade() -> None:
    op.drop_table('refresh_tokens')
    op.drop_table('driver_ratings')
    op.drop_table('audit_logs')
    op.drop_table('notifications')
    op.drop_table('offer_usage')
    op.drop_table('payments')
    op.drop_table('locations')
    op.drop_table('deliveries')
    op.drop_table('offers')
    op.drop_table('drivers')
    op.drop_table('users')
