# Import all models to ensure they're registered with SQLAlchemy
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.questions import Question, QuestionStatus, QuestionPriority, QuestionMessage, MessageType
from app.models.answers import Answer, AnswerSource
from app.models.automation import AutomationRule, AutomationRuleEmbedding, AutomationLog, AutomationLogAction

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "Organization",
    "User",
    "UserRole",
    "Question",
    "QuestionStatus",
    "QuestionPriority",
    "QuestionMessage",
    "MessageType",
    "Answer",
    "AnswerSource",
    "AutomationRule",
    "AutomationRuleEmbedding",
    "AutomationLog",
    "AutomationLogAction",
]
