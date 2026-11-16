"""Modelli ORM. Importare da qui per registrare tutte le tabelle nei metadata."""

from .activity import ActivityLog
from .agents import AgentStep, ResearchRun
from .collab import ProjectComment, SeriesAlert
from .connector import ConnectorState
from .discovery import DiscoveryAnalysis, DiscoveryAnomaly, DiscoveryConnection, DiscoveryHypothesis, DiscoverySession
from .filesafety import DeletedDocument, SystemCheck
from .finance import Credential, Observation, Series
from .document import Document, DocumentChunk
from .graph import Entity, Relation
from .lab import SimulationRun
from .history import EventSource, HistoricalEvent, KnowledgeItem
from .notification import Notification
from .preference import UserPreference
from .project import Project
from .project_item import ProjectItem
from .search import SearchQuery
from .source import Source
from .studio import Briefing, Note, Report, ReportSection, ReportSectionVersion
from .user import AuthSession, ProjectMember, User

__all__ = [
    "DiscoveryAnalysis",
    "DiscoveryAnomaly",
    "DiscoveryConnection",
    "DiscoveryHypothesis",
    "DiscoverySession",
    "ProjectComment",
    "ProjectItem",
    "SeriesAlert",
    "ActivityLog",
    "AuthSession",
    "ProjectMember",
    "Briefing",
    "Note",
    "Report",
    "ReportSection",
    "ReportSectionVersion",
    "DeletedDocument",
    "SystemCheck",
    "AgentStep",
    "ResearchRun",
    "ConnectorState",
    "Credential",
    "Observation",
    "Series",
    "Document",
    "DocumentChunk",
    "Entity",
    "EventSource",
    "HistoricalEvent",
    "KnowledgeItem",
    "Relation",
    "Notification",
    "Project",
    "SearchQuery",
    "SimulationRun",
    "Source",
    "User",
    "UserPreference",
]
