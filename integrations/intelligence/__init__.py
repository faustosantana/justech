"""Módulos de inteligencia JAIOS — stubs e interfaces (sin implementación de negocio)."""

from integrations.intelligence.documents import DGCPDocumentType, DocumentFillRequest
from integrations.intelligence.memory import EnterpriseMemoryStore, MemoryKind, MemoryRecord
from integrations.intelligence.microsoft365 import M365DriveItem, M365IntelligenceSource, M365MailboxItem
from integrations.intelligence.multi_agent import AgentOrchestrator, AgentRunRequest, AgentRunResult
from integrations.intelligence.notifications import NotificationChannel, NotificationDispatcher, NotificationPayload
from integrations.intelligence.price import PriceRecommendation, PriceSource
from integrations.intelligence.search import EnterpriseSearchIndex, IndexSource, SearchHit
from integrations.intelligence.supplier import SupplierQuote
from integrations.intelligence.tasks import TaskItem, TaskPriority, TaskSource
from integrations.intelligence.work_hub import WorkHubAggregator, WorkHubEntry

__all__ = [
    "DGCPDocumentType",
    "DocumentFillRequest",
    "EnterpriseMemoryStore",
    "EnterpriseSearchIndex",
    "IndexSource",
    "M365DriveItem",
    "M365IntelligenceSource",
    "M365MailboxItem",
    "MemoryKind",
    "MemoryRecord",
    "NotificationChannel",
    "NotificationDispatcher",
    "NotificationPayload",
    "PriceRecommendation",
    "PriceSource",
    "SearchHit",
    "SupplierQuote",
    "TaskItem",
    "TaskPriority",
    "TaskSource",
    "WorkHubAggregator",
    "WorkHubEntry",
    "AgentOrchestrator",
    "AgentRunRequest",
    "AgentRunResult",
]
