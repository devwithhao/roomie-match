"""add_user_preferences

Revision ID: 008_add_user_preferences
Revises: 007_add_packages
Create Date: 2026-05-23 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_add_user_preferences'
down_revision = '007_add_packages'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'user_preferences',
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('budget_min', sa.Integer(), nullable=True),
        sa.Column('budget_max', sa.Integer(), nullable=True),
        sa.Column('target_city', sa.String(length=100), nullable=True),
        sa.Column('target_district', sa.String(length=100), nullable=True),
        sa.Column('target_gender', sa.String(length=20), nullable=True),
        sa.Column('habit', sa.JSON(), nullable=True),
        sa.Column('introduce', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name='fk_user_preferences_account'),
        sa.PrimaryKeyConstraint('account_id')
    )

def downgrade() -> None:
    op.drop_table('user_preferences')
