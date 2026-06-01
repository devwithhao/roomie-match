"""add_matching_tables

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
    # 1. user_preferences
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

    # 2. Add socials to profiles
    op.add_column('profiles', sa.Column('facebook', sa.String(255), nullable=True))
    op.add_column('profiles', sa.Column('instagram', sa.String(255), nullable=True))
    op.add_column('profiles', sa.Column('twitter', sa.String(255), nullable=True))

    # 3. Create user_matches table
    op.create_table(
        'user_matches',
        sa.Column('account_id_1', sa.Integer(), nullable=False),
        sa.Column('account_id_2', sa.Integer(), nullable=False),
        sa.Column('is_matched', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id_1'], ['accounts.id'], name='fk_user_matches_account_1'),
        sa.ForeignKeyConstraint(['account_id_2'], ['accounts.id'], name='fk_user_matches_account_2'),
        sa.PrimaryKeyConstraint('account_id_1', 'account_id_2')
    )

    # 4. Create user_rejects table
    op.create_table(
        'user_rejects',
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('rejected_account_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name='fk_user_rejects_account'),
        sa.ForeignKeyConstraint(['rejected_account_id'], ['accounts.id'], name='fk_user_rejects_rejected_account'),
        sa.PrimaryKeyConstraint('account_id', 'rejected_account_id')
    )

def downgrade() -> None:
    op.drop_table('user_rejects')
    op.drop_table('user_matches')
    op.drop_column('profiles', 'twitter')
    op.drop_column('profiles', 'instagram')
    op.drop_column('profiles', 'facebook')
    op.drop_table('user_preferences')
