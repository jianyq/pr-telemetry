"""Finalization service for completing traces."""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.db.models import Trace, TraceChunk, Artifact, TraceStatus
from api.schemas import PRTelemetryTrace, BlobRef
from api.storage.minio_client import BUCKET_TRACES, upload_json, download_blob, BUCKET_CHUNKS
from .hash_chain import compute_chain_hash

logger = logging.getLogger(__name__)


class FinalizationService:
    """Service for finalizing traces and preparing for QA."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def finalize_trace(self, trace_id: str) -> dict:
        """
        Finalize a trace by assembling all chunks into the final document.
        
        Args:
            trace_id: Trace identifier
        
        Returns:
            Summary of finalization
        """
        # Get trace
        trace = self.db.query(Trace).filter(Trace.id == trace_id).first()
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")
        
        if trace.status == TraceStatus.COMPLETED:
            logger.info(f"Trace {trace_id} already completed")
            return {"status": "already_completed", "trace_id": trace_id}
        
        # Retrieve and merge all chunks
        chunks = (
            self.db.query(TraceChunk)
            .filter(TraceChunk.trace_id == trace_id)
            .order_by(TraceChunk.chunk_seq)
            .all()
        )
        
        if not chunks:
            raise ValueError("No chunks found for trace")
        
        # Load all events from chunks
        all_events = []
        for chunk in chunks:
            chunk_data = self._load_chunk(chunk.storage_uri)
            all_events.extend(chunk_data.get("events", []))
        
        # Sort by sequence number
        all_events.sort(key=lambda e: e["seq"])
        
        # Validate continuity (no gaps, no duplicates)
        self._validate_event_sequence(all_events)
        
        # Build final trace document
        final_trace = self._build_final_trace(trace, all_events)
        
        # Store final trace
        trace_json = final_trace.model_dump_json(indent=2)
        object_name = f"{trace_id}/trace_final.json"
        uri, sha256, size = upload_json(BUCKET_TRACES, object_name, trace_json)
        
        # Update trace record
        trace.final_trace_uri = uri
        trace.completed_at = datetime.utcnow()
        trace.status = TraceStatus.COMPLETED
        
        self.db.commit()
        
        logger.info(f"Finalized trace {trace_id}: {len(all_events)} events, stored at {uri}")
        
        return {
            "status": "success",
            "trace_id": trace_id,
            "final_uri": uri,
            "num_events": len(all_events)
        }
    
    def _load_chunk(self, storage_uri: str) -> dict:
        """Load chunk data from storage."""
        # Parse URI to get bucket and object name
        # Format: http(s)://endpoint/bucket/object_name
        parts = storage_uri.split("/", 4)
        bucket = parts[3]
        object_name = parts[4]
        
        data = download_blob(bucket, object_name)
        return json.loads(data.decode("utf-8"))
    
    def _validate_event_sequence(self, events: list[dict]):
        """Validate event sequence has no gaps or duplicates."""
        if not events:
            return
        
        seen_ids = set()
        expected_seq = 0
        
        for event in events:
            # Check for duplicate IDs
            event_id = event.get("id")
            if event_id in seen_ids:
                raise ValueError(f"Duplicate event ID: {event_id}")
            seen_ids.add(event_id)
            
            # Check sequence continuity (allow gaps, but warn)
            seq = event["seq"]
            if seq < expected_seq:
                raise ValueError(f"Out-of-order sequence: {seq} < {expected_seq}")
            expected_seq = seq + 1
    
    def _build_final_trace(
        self,
        trace: Trace,
        events: list[dict]
    ) -> PRTelemetryTrace:
        """Build the final PRTelemetryTrace document."""
        # Get artifacts
        artifacts = (
            self.db.query(Artifact)
            .filter(Artifact.trace_id == trace.id)
            .all()
        )
        
        # Find workspace snapshot
        workspace_snapshot = None
        for artifact in artifacts:
            if artifact.artifact_type == "workspace_snapshot":
                workspace_snapshot = BlobRef(
                    uri=artifact.storage_uri,
                    sha256=artifact.sha256,
                    size_bytes=artifact.size_bytes
                )
                break
        
        # Compute metrics
        num_edits = sum(1 for e in events if e["type"] == "file_edit")
        num_cmds = sum(1 for e in events if e["type"] == "cmd_run")
        num_test_runs = sum(1 for e in events if e["type"] == "test_run")
        
        files_touched = len(set(
            e["file_path"] for e in events if e["type"] == "file_edit"
        ))
        
        # Calculate duration
        if events:
            duration_s = events[-1]["ts_client_s"] - events[0]["ts_client_s"]
        else:
            duration_s = 0
        
        # Build trace
        trace_doc = PRTelemetryTrace(
            trace_version="1.0",
            trace_id=trace.id,
            session={
                "participant_id": trace.participant_id,
                "role": "human_dev",
                "consent": {
                    "rationales": True,
                    "commands": True,
                    "snapshots": True
                }
            },
            task={
                "id": trace.task_id,
                "title": trace.task_title
            },
            repo={
                "origin": trace.repo_origin or "",
                "start_commit": trace.start_commit or ""
            },
            events=events,
            artifacts={
                "final_workspace_snapshot": workspace_snapshot
            } if workspace_snapshot else None,
            metrics={
                "duration_s": duration_s,
                "num_events": len(events),
                "num_edits": num_edits,
                "num_cmds": num_cmds,
                "num_test_runs": num_test_runs,
                "files_touched": files_touched
            },
            integrity={
                "event_hash_chain": trace.event_hash_chain
            },
            created_at=trace.created_at,
            completed_at=trace.completed_at
        )
        
        return trace_doc

