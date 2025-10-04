"""
Pydantic models for PR Telemetry Trace v1.0
Mirrors the JSON schema defined in the project spec.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class ParticipantRole(str, Enum):
    """Role of the participant."""
    HUMAN_DEV = "human_dev"


# ============================================================================
# Supporting Models
# ============================================================================

class ConsentSettings(BaseModel):
    """Consent settings for data collection."""
    rationales: bool = Field(..., description="Consent to collect reasoning/rationales")
    commands: bool = Field(..., description="Consent to collect command outputs")
    snapshots: bool = Field(..., description="Consent to collect workspace snapshots")


class ClientClock(BaseModel):
    """Client clock information."""
    tz: Optional[str] = Field(None, description="Timezone (e.g., 'America/New_York')")
    start_unix_s: Optional[float] = Field(None, description="Session start time (Unix seconds)")


class Session(BaseModel):
    """Session metadata about the participant."""
    participant_id: str = Field(..., description="Anonymized participant identifier")
    role: ParticipantRole = Field(default=ParticipantRole.HUMAN_DEV, description="Role of participant")
    consent: ConsentSettings = Field(..., description="Data collection consent")
    client_clock: Optional[ClientClock] = Field(None, description="Client clock information")


class Task(BaseModel):
    """Task/bug being fixed."""
    id: str = Field(..., description="Task identifier")
    title: str = Field(..., description="Task title/summary")
    description: Optional[str] = Field(None, description="Detailed task description")
    known_failing_tests: Optional[list[str]] = Field(
        default=None,
        description="Known failing test names"
    )


class LanguageStat(BaseModel):
    """Language distribution in repository."""
    lang: str = Field(..., description="Programming language")
    ratio: float = Field(..., ge=0.0, le=1.0, description="Proportion of codebase")


class Repo(BaseModel):
    """Repository information."""
    origin: str = Field(..., description="Repository origin (URL or label)")
    branch: Optional[str] = Field(None, description="Git branch")
    start_commit: str = Field(..., description="Git commit SHA at session start")
    language_stats: Optional[list[LanguageStat]] = Field(
        None,
        description="Language distribution"
    )


class Environment(BaseModel):
    """Development environment information."""
    os: Optional[str] = Field(None, description="Operating system")
    ide_version: Optional[str] = Field(None, description="IDE version")
    tools: Optional[list[str]] = Field(None, description="Development tools available")


class BlobRef(BaseModel):
    """Reference to a stored blob (artifact)."""
    uri: str = Field(..., description="Storage URI (e.g., s3://bucket/key)")
    sha256: str = Field(..., description="SHA-256 hash of content")
    size_bytes: int = Field(..., ge=0, description="Size in bytes")


# ============================================================================
# Event Models
# ============================================================================

class BaseEvent(BaseModel):
    """Base event with common fields."""
    id: str = Field(..., description="Unique event identifier")
    seq: int = Field(..., ge=0, description="Sequence number (ordered)")
    ts_client_s: float = Field(..., description="Client timestamp (Unix seconds)")
    ts_server_s: float = Field(..., description="Server receive timestamp (Unix seconds)")
    type: str = Field(..., description="Event type discriminator")


class FileEditEvent(BaseEvent):
    """File edit event."""
    type: Literal["file_edit"] = "file_edit"
    file_path: str = Field(..., description="Path to edited file")
    language: Optional[str] = Field(None, description="Programming language")
    diff_unified: str = Field(..., description="Unified diff of changes")
    buffer_hash_before: Optional[str] = Field(None, description="SHA-256 before edit")
    buffer_hash_after: str = Field(..., description="SHA-256 after edit")
    edit_bytes: Optional[int] = Field(None, ge=0, description="Bytes changed")


class CmdRunEvent(BaseEvent):
    """Command execution event."""
    type: Literal["cmd_run"] = "cmd_run"
    cmd: str = Field(..., description="Command executed")
    cwd: Optional[str] = Field(None, description="Working directory")
    env_redacted: Optional[bool] = Field(False, description="Whether env vars were redacted")
    exit_code: int = Field(..., description="Exit code")
    stdout_ref: Optional[BlobRef] = Field(None, description="Reference to stdout blob")
    stderr_ref: Optional[BlobRef] = Field(None, description="Reference to stderr blob")


class TestRunEvent(BaseEvent):
    """Test execution event."""
    type: Literal["test_run"] = "test_run"
    framework: str = Field(..., description="Test framework (e.g., 'pytest')")
    selection: Optional[str] = Field(None, description="Test selection pattern")
    num_passed: int = Field(..., ge=0, description="Number of tests passed")
    num_failed: int = Field(..., ge=0, description="Number of tests failed")
    failed_tests: Optional[list[str]] = Field(None, description="Names of failed tests")
    report_ref: Optional[BlobRef] = Field(None, description="Reference to test report")


class CommitEvent(BaseEvent):
    """Git commit event."""
    type: Literal["commit"] = "commit"
    sha: str = Field(..., description="Commit SHA")
    parent_sha: Optional[str] = Field(None, description="Parent commit SHA")
    message: str = Field(..., description="Commit message")
    diff_unified: Optional[str] = Field(None, description="Unified diff of commit")


class StructuredRationale(BaseModel):
    """Structured reasoning/rationale."""
    plan: Optional[str] = Field(None, description="Plan or strategy")
    hypothesis: Optional[str] = Field(None, description="Hypothesis about the issue")
    observation: Optional[str] = Field(None, description="Observation from testing/debugging")
    decision: Optional[str] = Field(None, description="Decision made")
    next_step: Optional[str] = Field(None, description="Next action to take")


class RationaleNoteEvent(BaseEvent):
    """Rationale/reasoning note event."""
    type: Literal["rationale_note"] = "rationale_note"
    structured: Optional[StructuredRationale] = Field(
        None,
        description="Structured rationale fields"
    )
    freeform: Optional[str] = Field(None, description="Free-form reasoning (optional)")


# Union type for all events
TraceEvent = Union[
    FileEditEvent,
    CmdRunEvent,
    TestRunEvent,
    CommitEvent,
    RationaleNoteEvent,
]


# ============================================================================
# Artifacts & Metrics
# ============================================================================

class Artifacts(BaseModel):
    """Final artifacts from the session."""
    final_workspace_snapshot: Optional[BlobRef] = Field(
        None,
        description="Tarball of final workspace state"
    )
    final_patch_unified: Optional[str] = Field(
        None,
        description="Unified diff of all changes"
    )


class Metrics(BaseModel):
    """Summary metrics for the trace."""
    duration_s: Optional[float] = Field(None, ge=0, description="Session duration in seconds")
    num_events: Optional[int] = Field(None, ge=0, description="Total number of events")
    num_edits: Optional[int] = Field(None, ge=0, description="Number of file edits")
    num_cmds: Optional[int] = Field(None, ge=0, description="Number of commands run")
    num_test_runs: Optional[int] = Field(None, ge=0, description="Number of test runs")
    files_touched: Optional[int] = Field(None, ge=0, description="Unique files edited")
    edit_churn_lines: Optional[int] = Field(None, ge=0, description="Total lines changed")


# ============================================================================
# QA & Validation
# ============================================================================

class Validation(BaseModel):
    """Automated validation results."""
    tests_passed: Optional[bool] = Field(None, description="Whether all tests passed")
    framework: Optional[str] = Field(None, description="Test framework used")
    num_passed: Optional[int] = Field(None, ge=0, description="Number of tests passed")
    num_failed: Optional[int] = Field(None, ge=0, description="Number of tests failed")
    runtime_s: Optional[float] = Field(None, ge=0, description="Test runtime in seconds")
    container_image: Optional[str] = Field(None, description="Docker image used")
    log: Optional[BlobRef] = Field(None, description="Reference to validation log")


class JudgeScores(BaseModel):
    """LLM judge scoring rubric."""
    problem_understanding: Optional[float] = Field(
        None, ge=0, le=5,
        description="Score for problem understanding (0-5)"
    )
    causal_linking: Optional[float] = Field(
        None, ge=0, le=5,
        description="Score for causal reasoning (0-5)"
    )
    experiment_design: Optional[float] = Field(
        None, ge=0, le=5,
        description="Score for experiment design (0-5)"
    )
    efficiency: Optional[float] = Field(
        None, ge=0, le=5,
        description="Score for efficiency (0-5)"
    )
    reproducibility: Optional[float] = Field(
        None, ge=0, le=5,
        description="Score for reproducibility (0-5)"
    )
    safety_hygiene: Optional[float] = Field(
        None, ge=0, le=5,
        description="Score for safety & hygiene (0-5)"
    )
    overall: Optional[float] = Field(
        None, ge=0, le=5,
        description="Overall weighted score (0-5)"
    )


class Judge(BaseModel):
    """LLM judge evaluation."""
    model: Optional[str] = Field(None, description="Model used for judging")
    model_version: Optional[str] = Field(None, description="Model version")
    rubric_version: Optional[str] = Field(None, description="Rubric version")
    scores: Optional[JudgeScores] = Field(None, description="Rubric scores")
    feedback_summary: Optional[str] = Field(None, description="Summary feedback from judge")


class QA(BaseModel):
    """Quality assurance results."""
    validation: Optional[Validation] = Field(None, description="Automated validation")
    judge: Optional[Judge] = Field(None, description="LLM judge evaluation")


# ============================================================================
# Integrity
# ============================================================================

class Integrity(BaseModel):
    """Integrity and provenance information."""
    event_hash_chain: Optional[str] = Field(
        None,
        description="Hash chain of all events (HMAC)"
    )
    schema_hash: Optional[str] = Field(
        None,
        description="Hash of the schema version"
    )


# ============================================================================
# Top-Level Trace
# ============================================================================

class PRTelemetryTrace(BaseModel):
    """
    Top-level PR Telemetry Trace document.
    Captures a complete bug-fixing session from initial state to verified fix.
    """
    trace_version: Literal["1.0"] = "1.0"
    trace_id: str = Field(..., description="Unique trace identifier")
    
    session: Session = Field(..., description="Session metadata")
    task: Task = Field(..., description="Task being performed")
    repo: Repo = Field(..., description="Repository information")
    environment: Optional[Environment] = Field(None, description="Development environment")
    
    events: list[TraceEvent] = Field(
        default_factory=list,
        description="Ordered list of events"
    )
    
    artifacts: Optional[Artifacts] = Field(None, description="Final artifacts")
    metrics: Optional[Metrics] = Field(None, description="Summary metrics")
    qa: Optional[QA] = Field(None, description="Quality assurance results")
    integrity: Optional[Integrity] = Field(None, description="Integrity information")
    
    created_at: datetime = Field(..., description="Trace creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Trace completion timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "trace_version": "1.0",
                "trace_id": "trace-123",
                "session": {
                    "participant_id": "user-456",
                    "role": "human_dev",
                    "consent": {
                        "rationales": True,
                        "commands": True,
                        "snapshots": True
                    }
                },
                "task": {
                    "id": "task-789",
                    "title": "Fix failing test_add function"
                },
                "repo": {
                    "origin": "https://github.com/example/repo",
                    "start_commit": "abc123"
                },
                "events": [],
                "created_at": "2025-10-04T12:00:00Z"
            }
        }

    @field_validator("events")
    @classmethod
    def validate_event_sequence(cls, events: list[TraceEvent]) -> list[TraceEvent]:
        """Validate that events have monotonically increasing sequence numbers."""
        if not events:
            return events
        
        seen_seqs = set()
        for event in events:
            if event.seq in seen_seqs:
                raise ValueError(f"Duplicate sequence number: {event.seq}")
            seen_seqs.add(event.seq)
        
        # Verify ordering
        sorted_events = sorted(events, key=lambda e: e.seq)
        if sorted_events != events:
            raise ValueError("Events must be ordered by sequence number")
        
        return events

