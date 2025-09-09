"""Merge heads for analytics indexes

Revision ID: 12f93173f8ff
Revises: 043_add_media_assets_table, 6fcba57ecf58
Create Date: 2025-09-09 12:35:51.061398

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '12f93173f8ff'
down_revision = ('043_add_media_assets_table', '6fcba57ecf58')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass