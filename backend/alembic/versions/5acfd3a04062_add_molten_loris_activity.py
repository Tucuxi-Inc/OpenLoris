"""add_molten_loris_activity

Revision ID: 5acfd3a04062
Revises: 922ab34fc65c
Create Date: 2026-02-01

Adds the molten_loris_activities table for tracking MoltenLoris
Slack bot Q&A activity and expert corrections.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5acfd3a04062'
down_revision: Union[str, None] = '922ab34fc65c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'molten_loris_activities',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        # Organization
        sa.Column('organization_id', sa.UUID(), nullable=False),

        # Slack context
        sa.Column('channel_id', sa.String(100), nullable=False),
        sa.Column('channel_name', sa.String(255), nullable=False),
        sa.Column('thread_ts', sa.String(50), nullable=True),
        sa.Column('user_slack_id', sa.String(50), nullable=True),
        sa.Column('user_name', sa.String(255), nullable=True),

        # Q&A content
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('source_facts', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),

        # Correction tracking
        sa.Column('was_corrected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('corrected_by_id', sa.UUID(), nullable=True),
        sa.Column('corrected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correction_text', sa.Text(), nullable=True),
        sa.Column('correction_reason', sa.String(500), nullable=True),

        # Links to main system
        sa.Column('created_question_id', sa.UUID(), nullable=True),
        sa.Column('created_fact_id', sa.UUID(), nullable=True),

        # Primary key and foreign keys
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['corrected_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_question_id'], ['questions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_fact_id'], ['wisdom_facts.id'], ondelete='SET NULL'),
    )

    # Create indexes
    op.create_index(
        'idx_molten_activity_org',
        'molten_loris_activities',
        ['organization_id']
    )
    op.create_index(
        'idx_molten_activity_created',
        'molten_loris_activities',
        ['created_at'],
        postgresql_ops={'created_at': 'DESC'}
    )
    op.create_index(
        'idx_molten_activity_channel',
        'molten_loris_activities',
        ['organization_id', 'channel_id']
    )


def downgrade() -> None:
    op.drop_index('idx_molten_activity_channel', table_name='molten_loris_activities')
    op.drop_index('idx_molten_activity_created', table_name='molten_loris_activities')
    op.drop_index('idx_molten_activity_org', table_name='molten_loris_activities')
    op.drop_table('molten_loris_activities')
