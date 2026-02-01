#!/usr/bin/env python3
"""
Seed script for demo/screenshot data.
Creates realistic test data across all entities for documentation screenshots.

Run with: docker exec loris-backend-1 python scripts/seed_demo_data.py
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.core.database import AsyncSessionLocal, engine
from app.models import (
    Organization, User, UserRole,
    Question, QuestionStatus, QuestionPriority,
    Answer, AnswerSource,
    AutomationRule, AutomationLog, AutomationLogAction,
    WisdomFact, WisdomTier,
    KnowledgeDocument, ParsingStatus, ExtractionStatus,
    SubDomain, ExpertSubDomainAssignment,
    Notification, NotificationType,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo organization
ORG_NAME = "Acme Corporation"
ORG_SLUG = "acme-corp"

# Demo users
DEMO_USERS = [
    {"name": "Alice Admin", "email": "alice@acme.corp", "role": UserRole.ADMIN},
    {"name": "Bob Expert", "email": "bob@acme.corp", "role": UserRole.DOMAIN_EXPERT},
    {"name": "Carol Expert", "email": "carol@acme.corp", "role": UserRole.DOMAIN_EXPERT},
    {"name": "Dan Expert", "email": "dan@acme.corp", "role": UserRole.DOMAIN_EXPERT},
    {"name": "Eve User", "email": "eve@acme.corp", "role": UserRole.BUSINESS_USER},
    {"name": "Frank User", "email": "frank@acme.corp", "role": UserRole.BUSINESS_USER},
    {"name": "Grace User", "email": "grace@acme.corp", "role": UserRole.BUSINESS_USER},
    {"name": "Henry User", "email": "henry@acme.corp", "role": UserRole.BUSINESS_USER},
]

# Sub-domains
SUBDOMAINS = [
    {"name": "Contracts & Agreements", "description": "Contract review, negotiations, terms and conditions"},
    {"name": "Employment Law", "description": "HR policies, employment agreements, workplace compliance"},
    {"name": "Intellectual Property", "description": "Patents, trademarks, copyrights, trade secrets"},
    {"name": "Compliance & Regulatory", "description": "Industry regulations, compliance requirements, audits"},
    {"name": "Corporate Governance", "description": "Board matters, corporate structure, fiduciary duties"},
]

# Sample questions with varied statuses
SAMPLE_QUESTIONS = [
    # Resolved questions
    {"text": "What is the standard notice period for terminating a vendor contract?", "status": QuestionStatus.RESOLVED, "subdomain": 0, "priority": QuestionPriority.NORMAL},
    {"text": "Can we use Creative Commons images in our marketing materials?", "status": QuestionStatus.RESOLVED, "subdomain": 2, "priority": QuestionPriority.LOW},
    {"text": "What documentation is required for GDPR compliance?", "status": QuestionStatus.RESOLVED, "subdomain": 3, "priority": QuestionPriority.HIGH},
    {"text": "How do we handle employee invention assignments?", "status": QuestionStatus.RESOLVED, "subdomain": 2, "priority": QuestionPriority.NORMAL},
    {"text": "What are the requirements for board meeting minutes?", "status": QuestionStatus.RESOLVED, "subdomain": 4, "priority": QuestionPriority.LOW},

    # Answered (awaiting feedback)
    {"text": "Is a verbal agreement legally binding for small purchases?", "status": QuestionStatus.ANSWERED, "subdomain": 0, "priority": QuestionPriority.LOW},
    {"text": "What is our policy on remote work arrangements?", "status": QuestionStatus.ANSWERED, "subdomain": 1, "priority": QuestionPriority.NORMAL},

    # Auto-answered
    {"text": "What is the company policy on vacation carryover?", "status": QuestionStatus.AUTO_ANSWERED, "subdomain": 1, "priority": QuestionPriority.LOW},
    {"text": "How long should we retain financial records?", "status": QuestionStatus.AUTO_ANSWERED, "subdomain": 3, "priority": QuestionPriority.NORMAL},

    # In progress
    {"text": "Can we modify the standard NDA for international partners?", "status": QuestionStatus.IN_PROGRESS, "subdomain": 0, "priority": QuestionPriority.HIGH},
    {"text": "What are the implications of the new data privacy regulations?", "status": QuestionStatus.IN_PROGRESS, "subdomain": 3, "priority": QuestionPriority.URGENT},

    # Pending in queue
    {"text": "Do we need special insurance for company events off-site?", "status": QuestionStatus.EXPERT_QUEUE, "subdomain": 3, "priority": QuestionPriority.NORMAL},
    {"text": "What is the process for registering a trademark internationally?", "status": QuestionStatus.EXPERT_QUEUE, "subdomain": 2, "priority": QuestionPriority.HIGH},
    {"text": "How should we handle a potential conflict of interest situation?", "status": QuestionStatus.EXPERT_QUEUE, "subdomain": 4, "priority": QuestionPriority.URGENT},
    {"text": "What clauses should we include in a software licensing agreement?", "status": QuestionStatus.EXPERT_QUEUE, "subdomain": 0, "priority": QuestionPriority.NORMAL},

    # Recently submitted
    {"text": "Can employees use personal devices for work email?", "status": QuestionStatus.SUBMITTED, "subdomain": 1, "priority": QuestionPriority.LOW},
    {"text": "What is our liability if a contractor causes damage?", "status": QuestionStatus.SUBMITTED, "subdomain": 0, "priority": QuestionPriority.NORMAL},
]

# Knowledge facts
KNOWLEDGE_FACTS = [
    # Tier 0A - Authoritative
    {"statement": "All vendor contracts over $50,000 require legal review before signing.", "category": "Contracts", "tier": WisdomTier.TIER_0A, "domain": "Contract Management"},
    {"statement": "Employee terminations require 30 days written notice unless for cause.", "category": "Employment", "tier": WisdomTier.TIER_0A, "domain": "HR Policy"},
    {"statement": "Financial records must be retained for 7 years per regulatory requirements.", "category": "Compliance", "tier": WisdomTier.TIER_0A, "domain": "Records Management"},
    {"statement": "Board meetings require 14 days advance notice to all directors.", "category": "Governance", "tier": WisdomTier.TIER_0A, "domain": "Corporate Governance"},
    {"statement": "All intellectual property created by employees belongs to the company.", "category": "IP", "tier": WisdomTier.TIER_0A, "domain": "Intellectual Property"},

    # Tier 0B - Expert validated
    {"statement": "NDAs should include a 2-year confidentiality period as standard.", "category": "Contracts", "tier": WisdomTier.TIER_0B, "domain": "Contract Management"},
    {"statement": "Remote work arrangements require manager approval and IT security review.", "category": "Employment", "tier": WisdomTier.TIER_0B, "domain": "HR Policy"},
    {"statement": "GDPR compliance requires documented data processing agreements with all vendors.", "category": "Compliance", "tier": WisdomTier.TIER_0B, "domain": "Data Privacy"},
    {"statement": "Trademark applications typically take 8-12 months for approval.", "category": "IP", "tier": WisdomTier.TIER_0B, "domain": "Intellectual Property"},
    {"statement": "Conflict of interest disclosures must be filed annually by all managers.", "category": "Governance", "tier": WisdomTier.TIER_0B, "domain": "Corporate Governance"},
    {"statement": "Software licensing agreements must include source code escrow provisions.", "category": "Contracts", "tier": WisdomTier.TIER_0B, "domain": "Contract Management"},
    {"statement": "Employee invention assignments require separate compensation acknowledgment.", "category": "IP", "tier": WisdomTier.TIER_0B, "domain": "Intellectual Property"},
    {"statement": "Vacation carryover is limited to 5 days per year, expires March 31.", "category": "Employment", "tier": WisdomTier.TIER_0B, "domain": "HR Policy"},

    # Tier 0C - AI generated (pending review)
    {"statement": "Standard contract termination notice is 30 days for services under $10,000.", "category": "Contracts", "tier": WisdomTier.TIER_0C, "domain": "Contract Management"},
    {"statement": "Creative Commons BY-SA images can be used with proper attribution.", "category": "IP", "tier": WisdomTier.TIER_0C, "domain": "Intellectual Property"},
    {"statement": "Company event insurance is recommended for gatherings over 50 attendees.", "category": "Compliance", "tier": WisdomTier.TIER_0C, "domain": "Risk Management"},
    {"statement": "International trademark registration follows the Madrid Protocol process.", "category": "IP", "tier": WisdomTier.TIER_0C, "domain": "Intellectual Property"},
    {"statement": "Verbal agreements under $500 may be enforceable but documentation recommended.", "category": "Contracts", "tier": WisdomTier.TIER_0C, "domain": "Contract Management"},
]

# Automation rules
AUTOMATION_RULES = [
    {"name": "Vacation Carryover Policy", "canonical_question": "What is the company policy on vacation carryover?", "canonical_answer": "Employees may carry over up to 5 days of unused vacation time to the following year. Carried-over days must be used by March 31st or they will expire. This policy applies to all full-time employees.", "category_filter": "HR Policy"},
    {"name": "Financial Records Retention", "canonical_question": "How long should we retain financial records?", "canonical_answer": "Financial records must be retained for a minimum of 7 years per regulatory requirements. This includes invoices, receipts, bank statements, and tax documents. Electronic storage is acceptable if properly backed up.", "category_filter": "Compliance"},
    {"name": "Standard NDA Period", "canonical_question": "What is the standard NDA confidentiality period?", "canonical_answer": "Our standard NDA includes a 2-year confidentiality period from the date of disclosure. For highly sensitive information, this can be extended to 5 years with legal approval.", "category_filter": "Contracts"},
]

# Documents
DOCUMENTS = [
    {"title": "Employee Handbook 2024", "filename": "employee_handbook_2024.pdf", "parsing": ParsingStatus.COMPLETED, "extraction": ExtractionStatus.COMPLETED, "fact_count": 45},
    {"title": "Vendor Contract Template", "filename": "vendor_contract_template.docx", "parsing": ParsingStatus.COMPLETED, "extraction": ExtractionStatus.COMPLETED, "fact_count": 12},
    {"title": "GDPR Compliance Guide", "filename": "gdpr_compliance_guide.pdf", "parsing": ParsingStatus.COMPLETED, "extraction": ExtractionStatus.COMPLETED, "fact_count": 28},
    {"title": "IP Policy Document", "filename": "ip_policy.pdf", "parsing": ParsingStatus.COMPLETED, "extraction": ExtractionStatus.COMPLETED, "fact_count": 15},
    {"title": "Board Governance Manual", "filename": "board_governance.pdf", "parsing": ParsingStatus.COMPLETED, "extraction": ExtractionStatus.EXTRACTING, "fact_count": 0},
    {"title": "Data Retention Policy", "filename": "data_retention_policy.pdf", "parsing": ParsingStatus.PENDING, "extraction": ExtractionStatus.PENDING, "fact_count": 0},
]


async def seed_data():
    """Main seeding function."""
    async with AsyncSessionLocal() as db:
        print("Starting demo data seed...")

        # Check if demo org already exists
        result = await db.execute(select(Organization).where(Organization.slug == ORG_SLUG))
        existing_org = result.scalar_one_or_none()

        if existing_org:
            print(f"Demo organization '{ORG_NAME}' already exists. Skipping seed.")
            print("To re-seed, reset the database first.")
            return

        # Create organization
        print("Creating organization...")
        org = Organization(
            name=ORG_NAME,
            slug=ORG_SLUG,
            settings={
                "departments": ["Engineering", "Sales", "Marketing", "Finance", "HR", "Legal"],
                "require_department": True,
                "turbo_loris": {
                    "enabled": True,
                    "default_threshold": 0.75,
                    "threshold_options": [0.50, 0.75, 0.90]
                }
            }
        )
        db.add(org)
        await db.flush()

        # Create users
        print("Creating users...")
        users = {}
        for user_data in DEMO_USERS:
            user = User(
                organization_id=org.id,
                email=user_data["email"],
                name=user_data["name"],
                hashed_password=pwd_context.hash("Demo1234"),
                role=user_data["role"],
                is_active=True,
            )
            db.add(user)
            users[user_data["email"]] = user
        await db.flush()

        # Get user references
        experts = [users["bob@acme.corp"], users["carol@acme.corp"], users["dan@acme.corp"]]
        business_users = [users["eve@acme.corp"], users["frank@acme.corp"], users["grace@acme.corp"], users["henry@acme.corp"]]

        # Create sub-domains
        print("Creating sub-domains...")
        subdomains = []
        for i, sd_data in enumerate(SUBDOMAINS):
            sd = SubDomain(
                organization_id=org.id,
                name=sd_data["name"],
                description=sd_data["description"],
                is_active=True,
                sla_hours=24 if i < 2 else 48,
            )
            db.add(sd)
            subdomains.append(sd)
        await db.flush()

        # Assign experts to sub-domains
        print("Assigning experts to sub-domains...")
        # Bob: Contracts, Employment
        # Carol: IP, Compliance
        # Dan: Governance, Contracts
        assignments = [
            (experts[0], subdomains[0]),  # Bob - Contracts
            (experts[0], subdomains[1]),  # Bob - Employment
            (experts[1], subdomains[2]),  # Carol - IP
            (experts[1], subdomains[3]),  # Carol - Compliance
            (experts[2], subdomains[4]),  # Dan - Governance
            (experts[2], subdomains[0]),  # Dan - Contracts
        ]
        for expert, sd in assignments:
            assignment = ExpertSubDomainAssignment(
                expert_id=expert.id,
                subdomain_id=sd.id,
            )
            db.add(assignment)
        await db.flush()

        # Create knowledge facts
        print("Creating knowledge facts...")
        facts = []
        for i, fact_data in enumerate(KNOWLEDGE_FACTS):
            days_ago = random.randint(1, 90)
            fact = WisdomFact(
                organization_id=org.id,
                content=fact_data["statement"],
                category=fact_data["category"],
                tier=fact_data["tier"],
                domain=fact_data["domain"],
                confidence_score=0.95 if fact_data["tier"] == WisdomTier.TIER_0A else 0.85 if fact_data["tier"] == WisdomTier.TIER_0B else 0.70,
                usage_count=random.randint(0, 25),
                good_until_date=(datetime.now(timezone.utc) + timedelta(days=random.randint(30, 365))).date(),
                created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
            )
            db.add(fact)
            facts.append(fact)
        await db.flush()

        # Create automation rules
        print("Creating automation rules...")
        rules = []
        for rule_data in AUTOMATION_RULES:
            rule = AutomationRule(
                organization_id=org.id,
                name=rule_data["name"],
                canonical_question=rule_data["canonical_question"],
                canonical_answer=rule_data["canonical_answer"],
                category_filter=rule_data["category_filter"],
                similarity_threshold=0.85,
                times_triggered=random.randint(5, 30),
                times_accepted=random.randint(3, 25),
                times_rejected=random.randint(0, 5),
                good_until_date=(datetime.now(timezone.utc) + timedelta(days=180)).date(),
                created_by_id=random.choice(experts).id,
            )
            db.add(rule)
            rules.append(rule)
        await db.flush()

        # Create documents
        print("Creating documents...")
        for doc_data in DOCUMENTS:
            days_ago = random.randint(5, 60)
            file_type = "pdf" if doc_data["filename"].endswith(".pdf") else "docx"
            doc = KnowledgeDocument(
                organization_id=org.id,
                title=doc_data["title"],
                original_filename=doc_data["filename"],
                file_path=f"/uploads/{doc_data['filename']}",
                file_size_bytes=random.randint(100000, 5000000),
                file_type=file_type,
                mime_type="application/pdf" if file_type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                parsing_status=doc_data["parsing"],
                extraction_status=doc_data["extraction"],
                extracted_facts_count=doc_data["fact_count"],
                good_until_date=(datetime.now(timezone.utc) + timedelta(days=random.randint(60, 365))).date(),
                uploaded_by_id=random.choice(experts).id,
                created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
            )
            db.add(doc)
        await db.flush()

        # Create questions
        print("Creating questions...")
        questions = []
        for i, q_data in enumerate(SAMPLE_QUESTIONS):
            days_ago = random.randint(0, 30)
            asker = random.choice(business_users)
            subdomain = subdomains[q_data["subdomain"]]

            question = Question(
                organization_id=org.id,
                asked_by_id=asker.id,
                original_text=q_data["text"],
                status=q_data["status"],
                priority=q_data["priority"],
                subdomain_id=subdomain.id,
                department=random.choice(["Engineering", "Sales", "Marketing", "Finance"]),
                created_at=datetime.now(timezone.utc) - timedelta(days=days_ago, hours=random.randint(0, 23)),
            )

            # Assign expert for in-progress questions
            if q_data["status"] == QuestionStatus.IN_PROGRESS:
                question.assigned_to_id = random.choice(experts).id

            db.add(question)
            questions.append((question, q_data))
        await db.flush()

        # Create answers for answered/resolved questions
        print("Creating answers...")
        for question, q_data in questions:
            if q_data["status"] in [QuestionStatus.ANSWERED, QuestionStatus.RESOLVED]:
                expert = random.choice(experts)
                answer = Answer(
                    question_id=question.id,
                    created_by_id=expert.id,
                    content=f"Based on our company policies and review, here is the guidance for your question:\n\n{generate_sample_answer(q_data['text'])}\n\nPlease let me know if you need any clarification.",
                    source=AnswerSource.EXPERT,
                    created_at=question.created_at + timedelta(hours=random.randint(2, 48)),
                )
                db.add(answer)

                if q_data["status"] == QuestionStatus.RESOLVED:
                    question.resolved_at = answer.created_at + timedelta(hours=random.randint(1, 24))
                    question.satisfaction_rating = random.choice([4, 5, 5, 5])  # Mostly positive

            elif q_data["status"] == QuestionStatus.AUTO_ANSWERED:
                # Create auto-answer from rule
                rule = random.choice(rules)
                answer = Answer(
                    question_id=question.id,
                    created_by_id=rule.created_by_id,  # Use rule creator as answer author
                    content=rule.canonical_answer,
                    source=AnswerSource.AUTOMATION,
                    created_at=question.created_at + timedelta(seconds=random.randint(1, 30)),
                )
                db.add(answer)

                # Create automation log - delivered
                log = AutomationLog(
                    rule_id=rule.id,
                    question_id=question.id,
                    action=AutomationLogAction.DELIVERED,
                    similarity_score=random.uniform(0.87, 0.98),
                )
                db.add(log)

        await db.flush()

        # Create some notifications
        print("Creating notifications...")
        for expert in experts:
            # Pending queue notification
            notif = Notification(
                user_id=expert.id,
                organization_id=org.id,
                type=NotificationType.QUESTION_ROUTED,
                title="New question in your queue",
                message="A new question about contracts has been routed to your sub-domain.",
                link_url="/expert/queue",
                is_read=random.choice([True, False]),
                created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48)),
            )
            db.add(notif)

        for user in business_users[:2]:
            notif = Notification(
                user_id=user.id,
                organization_id=org.id,
                type=NotificationType.QUESTION_ANSWERED,
                title="Your question has been answered",
                message="An expert has provided an answer to your question.",
                link_url="/dashboard",
                is_read=False,
                created_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24)),
            )
            db.add(notif)

        await db.commit()

        print("\n" + "="*60)
        print("Demo data seeding complete!")
        print("="*60)
        print(f"\nOrganization: {ORG_NAME}")
        print(f"\nDemo accounts (password: Demo1234):")
        for user_data in DEMO_USERS:
            print(f"  - {user_data['email']} ({user_data['role'].value})")
        print(f"\nCreated:")
        print(f"  - {len(DEMO_USERS)} users")
        print(f"  - {len(SUBDOMAINS)} sub-domains")
        print(f"  - {len(KNOWLEDGE_FACTS)} knowledge facts")
        print(f"  - {len(AUTOMATION_RULES)} automation rules")
        print(f"  - {len(DOCUMENTS)} documents")
        print(f"  - {len(SAMPLE_QUESTIONS)} questions")
        print("\nYou can now take screenshots with realistic data!")


def generate_sample_answer(question: str) -> str:
    """Generate a realistic-looking sample answer based on the question."""
    answers = {
        "notice period": "Standard vendor contract termination requires 30 days written notice. For contracts over $100,000, a 60-day notice period applies.",
        "Creative Commons": "Yes, Creative Commons BY-SA images can be used in marketing materials with proper attribution. Ensure the attribution is visible and includes the creator's name and license type.",
        "GDPR": "GDPR compliance requires: (1) Data processing agreements with all vendors, (2) Privacy impact assessments for new projects, (3) Documented consent mechanisms, (4) Data breach notification procedures.",
        "invention": "Employee invention assignments are governed by our IP Policy. All inventions created during employment using company resources belong to the company. Employees receive acknowledgment in the patent filing.",
        "board meeting": "Board meeting minutes must include: (1) Date, time, location, (2) Attendees and quorum confirmation, (3) Motions and voting results, (4) Action items assigned, (5) Signatures of chair and secretary.",
        "verbal agreement": "While verbal agreements may be legally binding, we strongly recommend documenting all agreements in writing for amounts over $500 to avoid disputes.",
        "remote work": "Remote work arrangements require: (1) Manager approval, (2) IT security assessment, (3) Signed remote work agreement, (4) Quarterly performance reviews.",
    }

    for key, answer in answers.items():
        if key.lower() in question.lower():
            return answer

    return "This matter has been reviewed according to our standard policies and procedures. The guidance above reflects our current best practices and regulatory requirements."


if __name__ == "__main__":
    asyncio.run(seed_data())
