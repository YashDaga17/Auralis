"""
SQLAlchemy ORM models for multi-tenant agent registry.
"""
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from database import Base


class Company(Base):
    """Multi-tenant company/organization."""
    __tablename__ = "companies"
    
    company_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    agents = relationship("Agent", back_populates="company")
    conversations = relationship("ConversationHistory", back_populates="company")
    user_preferences = relationship("UserPreference", back_populates="company")
    execution_metrics = relationship("ExecutionMetric", back_populates="company")


class Agent(Base):
    """Voice agent configuration with workflow JSON."""
    __tablename__ = "agents"
    
    agent_id = Column(String(255), primary_key=True)  # Vapi assistant_id
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    workflow_json = Column(JSONB, nullable=False)
    current_version_id = Column(UUID(as_uuid=True), ForeignKey("workflow_versions.version_id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="agents")
    versions = relationship("WorkflowVersion", back_populates="agent", foreign_keys="WorkflowVersion.agent_id")
    conversations = relationship("ConversationHistory", back_populates="agent")
    execution_metrics = relationship("ExecutionMetric", back_populates="agent")
    
    # Indexes
    __table_args__ = (
        Index("idx_agents_company", "company_id"),
    )


class WorkflowVersion(Base):
    """Version history for workflow configurations."""
    __tablename__ = "workflow_versions"
    
    version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    workflow_json = Column(JSONB, nullable=False)
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="versions", foreign_keys=[agent_id])


class ConversationHistory(Base):
    """Persistent conversation memory for each user session."""
    __tablename__ = "conversation_history"
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)
    agent_id = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_message = Column(Text)
    agent_response = Column(Text)
    extracted_entities = Column(JSONB)
    intent = Column(String(100))
    confidence = Column(Float)
    
    # Relationships
    company = relationship("Company", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")
    
    # Indexes
    __table_args__ = (
        Index("idx_conversation_user", "user_id", "timestamp"),
        Index("idx_conversation_agent", "agent_id", "timestamp"),
    )


class UserPreference(Base):
    """User-specific preferences for personalization."""
    __tablename__ = "user_preferences"
    
    user_id = Column(String(255), primary_key=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    agent_id = Column(String(255), ForeignKey("agents.agent_id"))
    communication_style = Column(String(50))  # 'concise', 'detailed', 'technical'
    preferred_sources = Column(JSONB)  # Array of collection names
    notification_preferences = Column(JSONB)
    
    # Relationships
    company = relationship("Company", back_populates="user_preferences")


class ExecutionMetric(Base):
    """Performance metrics for workflow executions."""
    __tablename__ = "execution_metrics"
    
    execution_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    total_duration_ms = Column(Integer)
    node_execution_times = Column(JSONB)  # {node_id: duration_ms}
    intent_classification_accuracy = Column(Float)
    user_satisfaction_score = Column(Integer)
    
    # Relationships
    company = relationship("Company", back_populates="execution_metrics")
    agent = relationship("Agent", back_populates="execution_metrics")
    
    # Indexes
    __table_args__ = (
        Index("idx_metrics_agent", "agent_id", "timestamp"),
    )
