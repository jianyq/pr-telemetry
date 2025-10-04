"""SQLAlchemy database models."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, DateTime, Integer, Boolean, Text, ForeignKey, JSON, Float, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class TraceStatus(str, PyEnum):
    """Status of a trace."""
    CREATED = "created"
    INGESTING = "ingesting"
    COMPLETED = "completed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    FAILED = "failed"


class Trace(Base):
    """Main trace record."""
    __tablename__ = "traces"

    id = Column(String, primary_key=True, index=True)  # trace_id
    status = Column(Enum(TraceStatus), default=TraceStatus.CREATED, nullable=False)
    
    # Metadata
    participant_id = Column(String, index=True, nullable=False)
    task_id = Column(String, index=True, nullable=False)
    task_title = Column(String, nullable=False)
    repo_origin = Column(String)
    start_commit = Column(String)
    
    # Upload token for authentication
    upload_token = Column(String, unique=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Event tracking
    num_events = Column(Integer, default=0)
    last_seq = Column(Integer, default=-1)
    
    # Hash chain for integrity
    event_hash_chain = Column(String)
    
    # Storage location of finalized trace JSON
    final_trace_uri = Column(String)
    
    # Relationships
    chunks = relationship("TraceChunk", back_populates="trace", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="trace", cascade="all, delete-orphan")
    qa_result = relationship("QAResult", back_populates="trace", uselist=False, cascade="all, delete-orphan")


class TraceChunk(Base):
    """Raw chunk uploaded during ingestion."""
    __tablename__ = "trace_chunks"

    id = Column(String, primary_key=True)  # chunk_id
    trace_id = Column(String, ForeignKey("traces.id"), nullable=False, index=True)
    chunk_seq = Column(Integer, nullable=False)
    
    # Storage location of raw chunk (JSONL)
    storage_uri = Column(String, nullable=False)
    
    # Metadata
    num_events = Column(Integer, default=0)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    
    trace = relationship("Trace", back_populates="chunks")
    
    class Config:
        indexes = [
            ("trace_id", "chunk_seq"),  # Composite index
        ]


class Artifact(Base):
    """Stored artifact (blob) associated with a trace."""
    __tablename__ = "artifacts"

    id = Column(String, primary_key=True)
    trace_id = Column(String, ForeignKey("traces.id"), nullable=False, index=True)
    
    # Artifact type (e.g., "stdout", "stderr", "test_report", "workspace_snapshot")
    artifact_type = Column(String, nullable=False)
    
    # Storage location and integrity
    storage_uri = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    
    # Optional context (e.g., event_id this artifact is associated with)
    event_id = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    trace = relationship("Trace", back_populates="artifacts")


class QAResult(Base):
    """QA validation and judge results for a trace."""
    __tablename__ = "qa_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String, ForeignKey("traces.id"), unique=True, nullable=False, index=True)
    
    # Validation results
    validation_tests_passed = Column(Boolean)
    validation_framework = Column(String)
    validation_num_passed = Column(Integer)
    validation_num_failed = Column(Integer)
    validation_runtime_s = Column(Float)
    validation_container_image = Column(String)
    validation_log_uri = Column(String)
    
    # Judge results
    judge_model = Column(String)
    judge_model_version = Column(String)
    judge_rubric_version = Column(String)
    judge_feedback_summary = Column(Text)
    
    # Scores (0-5)
    score_problem_understanding = Column(Float)
    score_causal_linking = Column(Float)
    score_experiment_design = Column(Float)
    score_efficiency = Column(Float)
    score_reproducibility = Column(Float)
    score_safety_hygiene = Column(Float)
    score_overall = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    trace = relationship("Trace", back_populates="qa_result")


class IdempotencyKey(Base):
    """Idempotency key tracking for API requests."""
    __tablename__ = "idempotency_keys"

    key = Column(String, primary_key=True, index=True)
    trace_id = Column(String, ForeignKey("traces.id"), nullable=False, index=True)
    endpoint = Column(String, nullable=False)
    
    # Response to return for duplicate requests
    response_status = Column(Integer)
    response_body = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

