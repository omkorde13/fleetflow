"""Widen users.avatar_url to support long Google profile picture URLs

Revision ID: 0002_avatar_url_text
Revises: 0001_initial
Create Date: 2026-06-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_avatar_url_text'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('users', 'avatar_url', type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'avatar_url', type_=sa.String(512), existing_nullable=True)
