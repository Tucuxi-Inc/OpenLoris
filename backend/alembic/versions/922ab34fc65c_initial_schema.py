"""initial_schema

Revision ID: 922ab34fc65c
Revises:
Create Date: 2026-02-01

This migration captures the existing Loris database schema.
Tables were created by init_db() and this migration is stamped
as the baseline for future migrations.

Tables included:
- organizations: Multi-tenant support
- users: User accounts with roles (business_user, domain_expert, admin)
- questions: Q&A workflow with status tracking
- question_messages: Clarification threading
- answers: Expert and automated answers
- automation_rules: Canonical Q&A pairs for auto-answering
- automation_rule_embeddings: Vector embeddings for rules
- automation_logs: Audit trail for automation
- wisdom_facts: Knowledge base facts with tiers
- wisdom_embeddings: Vector embeddings for facts
- knowledge_documents: Uploaded documents with GUD
- document_chunks: Parsed document segments
- chunk_embeddings: Vector embeddings for chunks
- extracted_fact_candidates: AI-extracted facts pending review
- departments: Organization departments
- notifications: In-app notifications
- subdomains: Sub-domain routing (e.g., Contracts, Employment Law)
- expert_subdomain_assignments: Expert to sub-domain mapping
- reassignment_requests: Sub-domain reassignment workflow
- question_routings: Question routing audit
- slack_captures: MoltenLoris Slack integration captures
- daily_metrics: Pre-aggregated metrics (future use)
- turbo_attributions: Turbo answer source attributions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '922ab34fc65c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Initial schema - tables already exist via init_db().

    This migration is stamped as the baseline. New databases should
    run init_db() first, then stamp this migration.

    For reference, here's the create order (respecting foreign keys):

    1. organizations
    2. users (FK: organization_id)
    3. subdomains (FK: organization_id)
    4. departments (FK: organization_id)
    5. questions (FK: organization_id, asked_by_id, assigned_to_id, subdomain_id)
    6. answers (FK: question_id, created_by_id)
    7. question_messages (FK: question_id, user_id)
    8. automation_rules (FK: organization_id, created_by_id, source_question_id)
    9. automation_rule_embeddings (FK: rule_id)
    10. automation_logs (FK: rule_id, question_id)
    11. wisdom_facts (FK: organization_id, validated_by_id, source_document_id)
    12. wisdom_embeddings (FK: wisdom_fact_id)
    13. knowledge_documents (FK: organization_id, uploaded_by_id, department_id)
    14. document_chunks (FK: document_id)
    15. chunk_embeddings (FK: chunk_id)
    16. extracted_fact_candidates (FK: document_id, chunk_id)
    17. notifications (FK: user_id, organization_id)
    18. expert_subdomain_assignments (FK: user_id, subdomain_id)
    19. reassignment_requests (FK: question_id, requested_by_id, subdomain_id)
    20. question_routings (FK: question_id, subdomain_id, expert_id)
    21. slack_captures (FK: organization_id)
    22. daily_metrics (FK: organization_id)
    23. turbo_attributions (FK: question_id, attributed_user_id)
    """
    pass


def downgrade() -> None:
    """
    Cannot downgrade from initial schema.
    Use DROP SCHEMA public CASCADE to reset.
    """
    pass
