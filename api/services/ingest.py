"""Ingestion service for processing trace chunks."""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from api.db.models import Trace, TraceChunk, Artifact, TraceStatus
from api.schemas import TraceEvent, BlobRef
from api.storage import storage_client
from api.storage.minio_client import (
    BUCKET_CHUNKS, BUCKET_ARTIFACTS, 
    upload_json, upload_blob
)
from .hash_chain import compute_event_hash

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting trace chunks and events."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def ingest_chunk(
        self,
        trace_id: str,
        chunk_id: str,
        chunk_seq: int,
        events: list[dict],
        artifacts: dict[str, Any] | None = None
    ) -> dict:
        """
        Ingest a chunk of events for a trace.
        
        Args:
            trace_id: Trace identifier
            chunk_id: Chunk identifier
            chunk_seq: Chunk sequence number
            events: List of event dictionaries
            artifacts: Optional artifacts in this chunk
        
        Returns:
            Summary of ingestion
        """
        # Get trace
        trace = self.db.query(Trace).filter(Trace.id == trace_id).first()
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")
        
        if trace.status == TraceStatus.COMPLETED:
            raise ValueError("Cannot ingest into completed trace")
        
        # Check for duplicate chunk
        existing_chunk = self.db.query(TraceChunk).filter(
            TraceChunk.id == chunk_id
        ).first()
        if existing_chunk:
            logger.info(f"Chunk {chunk_id} already ingested, skipping")
            return {"status": "duplicate", "chunk_id": chunk_id}
        
        # Store raw chunk to MinIO
        chunk_data = {
            "chunk_id": chunk_id,
            "chunk_seq": chunk_seq,
            "trace_id": trace_id,
            "events": events,
            "artifacts": artifacts,
            "received_at": datetime.utcnow().isoformat()
        }
        chunk_json = json.dumps(chunk_data, indent=2)
        
        object_name = f"{trace_id}/chunks/chunk_{chunk_seq:04d}_{chunk_id}.json"
        uri, sha256, size = upload_json(BUCKET_CHUNKS, object_name, chunk_json)
        
        # Create chunk record
        chunk = TraceChunk(
            id=chunk_id,
            trace_id=trace_id,
            chunk_seq=chunk_seq,
            storage_uri=uri,
            num_events=len(events)
        )
        self.db.add(chunk)
        
        # Process events
        events_added = 0
        for event_dict in events:
            # Add server timestamp
            event_dict["ts_server_s"] = datetime.utcnow().timestamp()
            
            # Update hash chain
            trace.event_hash_chain = compute_event_hash(
                event_dict,
                trace.event_hash_chain
            )
            
            # Track sequence
            if event_dict["seq"] > trace.last_seq:
                trace.last_seq = event_dict["seq"]
            
            events_added += 1
        
        # Process artifacts if present
        artifacts_added = 0
        if artifacts:
            artifacts_added = self._process_artifacts(trace_id, artifacts)
        
        # Update trace
        trace.num_events += events_added
        trace.status = TraceStatus.INGESTING
        
        self.db.commit()
        
        logger.info(
            f"Ingested chunk {chunk_id} for trace {trace_id}: "
            f"{events_added} events, {artifacts_added} artifacts"
        )
        
        return {
            "status": "success",
            "chunk_id": chunk_id,
            "events_added": events_added,
            "artifacts_added": artifacts_added,
            "total_events": trace.num_events
        }
    
    def _process_artifacts(
        self,
        trace_id: str,
        artifacts: dict[str, Any]
    ) -> int:
        """Process and store artifacts from a chunk."""
        count = 0
        
        for artifact_key, artifact_data in artifacts.items():
            if not artifact_data:
                continue
            
            # Determine artifact type and content
            if isinstance(artifact_data, dict) and "content" in artifact_data:
                content = artifact_data["content"]
                artifact_type = artifact_data.get("type", artifact_key)
                event_id = artifact_data.get("event_id")
            else:
                content = artifact_data
                artifact_type = artifact_key
                event_id = None
            
            # Upload to storage
            if isinstance(content, str):
                data = content.encode("utf-8")
            else:
                data = json.dumps(content).encode("utf-8")
            
            artifact_id = str(uuid4())
            object_name = f"{trace_id}/artifacts/{artifact_type}_{artifact_id}"
            uri, sha256, size = upload_blob(BUCKET_ARTIFACTS, object_name, data)
            
            # Create artifact record
            artifact = Artifact(
                id=artifact_id,
                trace_id=trace_id,
                artifact_type=artifact_type,
                storage_uri=uri,
                sha256=sha256,
                size_bytes=size,
                event_id=event_id
            )
            self.db.add(artifact)
            count += 1
        
        return count

