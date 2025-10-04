"""
PR Telemetry API - Main application
Handles ingestion, validation, and serving of PR telemetry traces.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.db import get_db, engine, Base
from api.db.models import Trace, IdempotencyKey, TraceStatus, QAResult
from api.services.ingest import IngestionService
from api.services.finalize import FinalizationService
from api.storage.minio_client import ensure_buckets, download_blob, BUCKET_TRACES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting PR Telemetry API...")
    
    # Migrations are handled by alembic in the startup command
    # No need to create tables here
    logger.info("Database ready (migrations handled by alembic)")
    
    # Ensure storage buckets exist
    try:
        ensure_buckets()
        logger.info("Storage buckets verified")
    except Exception as e:
        logger.error(f"Failed to ensure buckets: {e}")
        # Continue anyway - buckets might already exist
    
    yield
    
    logger.info("Shutting down PR Telemetry API...")


app = FastAPI(
    title="PR Telemetry API",
    description="API for collecting and analyzing developer bug-fixing traces",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateTraceRequest(BaseModel):
    """Request to create a new trace."""
    participant_id: str = Field(..., description="Anonymized participant ID")
    task_id: str = Field(..., description="Task identifier")
    task_title: str = Field(..., description="Task title")
    repo_origin: str | None = Field(None, description="Repository origin")
    start_commit: str | None = Field(None, description="Starting commit SHA")


class CreateTraceResponse(BaseModel):
    """Response from creating a trace."""
    trace_id: str
    upload_token: str
    message: str = "Trace created successfully"


class IngestChunkRequest(BaseModel):
    """Request to ingest a chunk of events."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    chunk_seq: int = Field(..., ge=0, description="Chunk sequence number")
    events: list[dict] = Field(..., description="List of events")
    artifacts: dict[str, Any] | None = Field(None, description="Optional artifacts")


class IngestChunkResponse(BaseModel):
    """Response from ingesting a chunk."""
    status: str
    chunk_id: str
    events_added: int = 0
    artifacts_added: int = 0
    total_events: int = 0


class CompleteTraceResponse(BaseModel):
    """Response from completing a trace."""
    status: str
    trace_id: str
    final_uri: str | None = None
    num_events: int = 0
    qa_job_id: str | None = None


# ============================================================================
# Authentication
# ============================================================================

AUTH_TOKEN = "dev_token_12345"  # In production, use proper auth


def verify_token(authorization: str = Header(...)) -> str:
    """Verify bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    token = authorization[7:]  # Remove "Bearer "
    if token != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return token


def verify_upload_token(
    trace_id: str,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> Trace:
    """Verify upload token for a specific trace."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    token = authorization[7:]
    
    trace = db.query(Trace).filter(Trace.id == trace_id).first()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    if trace.upload_token != token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid upload token for this trace"
        )
    
    return trace


# ============================================================================
# Idempotency
# ============================================================================

def check_idempotency(
    idempotency_key: str | None,
    trace_id: str,
    endpoint: str,
    db: Session
) -> tuple[bool, dict | None]:
    """
    Check if request with this idempotency key was already processed.
    
    Returns:
        (is_duplicate, previous_response)
    """
    if not idempotency_key:
        return False, None
    
    existing = db.query(IdempotencyKey).filter(
        IdempotencyKey.key == idempotency_key,
        IdempotencyKey.trace_id == trace_id,
        IdempotencyKey.endpoint == endpoint
    ).first()
    
    if existing:
        # Check if expired
        if existing.expires_at < datetime.utcnow():
            db.delete(existing)
            db.commit()
            return False, None
        return True, existing.response_body
    
    return False, None


def store_idempotency(
    idempotency_key: str,
    trace_id: str,
    endpoint: str,
    response_status: int,
    response_body: dict,
    db: Session
):
    """Store idempotency key and response."""
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    idem = IdempotencyKey(
        key=idempotency_key,
        trace_id=trace_id,
        endpoint=endpoint,
        response_status=response_status,
        response_body=response_body,
        expires_at=expires_at
    )
    db.add(idem)
    db.commit()


# ============================================================================
# Health Endpoints
# ============================================================================

@app.get("/healthz")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/readyz")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness check endpoint."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {
            "status": "ready",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


# ============================================================================
# Trace Management Endpoints
# ============================================================================

@app.post("/v1/traces", response_model=CreateTraceResponse)
def create_trace(
    request: CreateTraceRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_token)
):
    """Create a new trace."""
    trace_id = f"trace-{uuid4().hex[:12]}"
    upload_token = token_urlsafe(32)
    
    trace = Trace(
        id=trace_id,
        status=TraceStatus.CREATED,
        participant_id=request.participant_id,
        task_id=request.task_id,
        task_title=request.task_title,
        repo_origin=request.repo_origin,
        start_commit=request.start_commit,
        upload_token=upload_token
    )
    
    db.add(trace)
    db.commit()
    
    logger.info(f"Created trace: {trace_id}")
    
    return CreateTraceResponse(
        trace_id=trace_id,
        upload_token=upload_token
    )


@app.post("/v1/traces/{trace_id}/events:ingest", response_model=IngestChunkResponse)
def ingest_events(
    trace_id: str,
    request: IngestChunkRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    trace: Trace = Depends(verify_upload_token)
):
    """Ingest a chunk of events for a trace."""
    # Check idempotency
    is_duplicate, previous_response = check_idempotency(
        idempotency_key,
        trace_id,
        "ingest_events",
        db
    )
    if is_duplicate:
        logger.info(f"Duplicate request for chunk {request.chunk_id}")
        return IngestChunkResponse(**previous_response)
    
    # Ingest chunk
    try:
        service = IngestionService(db)
        result = service.ingest_chunk(
            trace_id=trace_id,
            chunk_id=request.chunk_id,
            chunk_seq=request.chunk_seq,
            events=request.events,
            artifacts=request.artifacts
        )
        
        response = IngestChunkResponse(**result)
        
        # Store idempotency
        if idempotency_key:
            store_idempotency(
                idempotency_key,
                trace_id,
                "ingest_events",
                200,
                result,
                db
            )
        
        return response
    
    except Exception as e:
        logger.error(f"Error ingesting chunk {request.chunk_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/traces/{trace_id}/complete", response_model=CompleteTraceResponse)
def complete_trace(
    trace_id: str,
    db: Session = Depends(get_db),
    trace: Trace = Depends(verify_upload_token)
):
    """
    Complete a trace and trigger QA validation.
    """
    try:
        # Finalize trace
        service = FinalizationService(db)
        result = service.finalize_trace(trace_id)
        
        # Queue QA job
        from worker.tasks import qa_validate_and_judge
        job = qa_validate_and_judge.delay(trace_id)
        
        logger.info(f"Queued QA job {job.id} for trace {trace_id}")
        
        return CompleteTraceResponse(
            **result,
            qa_job_id=job.id
        )
    
    except Exception as e:
        logger.error(f"Error completing trace {trace_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/traces/{trace_id}")
def get_trace(
    trace_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_token)
):
    """Get the finalized trace document."""
    trace = db.query(Trace).filter(Trace.id == trace_id).first()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    if not trace.final_trace_uri:
        # Trace not yet finalized
        return JSONResponse(
            status_code=202,
            content={
                "status": trace.status.value,
                "message": "Trace not yet finalized",
                "num_events": trace.num_events
            }
        )
    
    # Load trace from storage
    try:
        parts = trace.final_trace_uri.split("/", 4)
        bucket = parts[3]
        object_name = parts[4]
        
        data = download_blob(bucket, object_name)
        trace_dict = data.decode("utf-8")
        
        # Parse and potentially update with QA results
        import json
        trace_doc = json.loads(trace_dict)
        
        # Add QA results if available
        qa_result = db.query(QAResult).filter(
            QAResult.trace_id == trace_id
        ).first()
        
        if qa_result:
            trace_doc["qa"] = {
                "validation": {
                    "tests_passed": qa_result.validation_tests_passed,
                    "framework": qa_result.validation_framework,
                    "num_passed": qa_result.validation_num_passed,
                    "num_failed": qa_result.validation_num_failed,
                    "runtime_s": qa_result.validation_runtime_s,
                    "container_image": qa_result.validation_container_image
                } if qa_result.validation_tests_passed is not None else None,
                "judge": {
                    "model": qa_result.judge_model,
                    "model_version": qa_result.judge_model_version,
                    "rubric_version": qa_result.judge_rubric_version,
                    "scores": {
                        "problem_understanding": qa_result.score_problem_understanding,
                        "causal_linking": qa_result.score_causal_linking,
                        "experiment_design": qa_result.score_experiment_design,
                        "efficiency": qa_result.score_efficiency,
                        "reproducibility": qa_result.score_reproducibility,
                        "safety_hygiene": qa_result.score_safety_hygiene,
                        "overall": qa_result.score_overall
                    },
                    "feedback_summary": qa_result.judge_feedback_summary
                } if qa_result.judge_model else None
            }
        
        return JSONResponse(content=trace_doc)
    
    except Exception as e:
        logger.error(f"Error loading trace {trace_id}: {e}")
        raise HTTPException(status_code=500, detail="Error loading trace")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "PR Telemetry API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/healthz",
            "readiness": "/readyz",
            "create_trace": "POST /v1/traces",
            "ingest_events": "POST /v1/traces/{trace_id}/events:ingest",
            "complete_trace": "POST /v1/traces/{trace_id}/complete",
            "get_trace": "GET /v1/traces/{trace_id}"
        }
    }

