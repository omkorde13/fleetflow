"""Add pickup_otp and delivery_otp columns to deliveries

Revision ID: 0003_delivery_otp_columns
Revises: 0002_avatar_url_text
Create Date: 2026-06-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_delivery_otp_columns'
down_revision = '0002_avatar_url_text'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('deliveries', sa.Column('pickup_otp', sa.String(4), nullable=True))
    op.add_column('deliveries', sa.Column('delivery_otp', sa.String(4), nullable=True))


def downgrade() -> None:
    op.drop_column('deliveries', 'delivery_otp')
    op.drop_column('deliveries', 'pickup_otp')
