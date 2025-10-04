"""Celery tasks for QA validation and judging."""

import json
import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from api.db.models import Trace, QAResult, TraceStatus, Artifact
from api.db.session import SessionLocal
from api.storage.minio_client import download_blob, upload_blob, BUCKET_ARTIFACTS
from worker.celery_app import celery_app
from worker.qa.runner import TestRunner
from worker.judge.llm_judge import LLMJudge
from worker.judge.prompt import build_judge_prompt, RUBRIC_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@celery_app.task(name="worker.tasks.qa_validate_and_judge", bind=True)
def qa_validate_and_judge(self, trace_id: str):
    """
    Run QA validation and LLM judge for a completed trace.
    
    Args:
        trace_id: Trace identifier
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Starting QA for trace: {trace_id}")
        
        # Get trace
        trace = db.query(Trace).filter(Trace.id == trace_id).first()
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")
        
        # Update status
        trace.status = TraceStatus.VALIDATING
        db.commit()
        
        # Load trace document
        trace_doc = load_trace_document(trace.final_trace_uri)
        
        # Run validation
        validation_result = run_validation(trace_id, trace_doc, db)
        logger.info(f"Validation complete for {trace_id}: {validation_result.get('tests_passed')}")
        
        # Run LLM judge
        judge_result = run_judge(trace_doc)
        logger.info(f"Judge complete for {trace_id}: overall score {judge_result['scores'].get('overall')}")
        
        # Store results
        qa_result = QAResult(
            trace_id=trace_id,
            # Validation
            validation_tests_passed=validation_result.get("tests_passed"),
            validation_framework=validation_result.get("framework"),
            validation_num_passed=validation_result.get("num_passed"),
            validation_num_failed=validation_result.get("num_failed"),
            validation_runtime_s=validation_result.get("runtime_s"),
            validation_container_image=validation_result.get("container_image"),
            validation_log_uri=validation_result.get("log_uri"),
            # Judge
            judge_model=judge_result.get("model"),
            judge_model_version=judge_result.get("model_version"),
            judge_rubric_version=RUBRIC_VERSION,
            judge_feedback_summary=judge_result.get("feedback_summary"),
            score_problem_understanding=judge_result["scores"].get("problem_understanding"),
            score_causal_linking=judge_result["scores"].get("causal_linking"),
            score_experiment_design=judge_result["scores"].get("experiment_design"),
            score_efficiency=judge_result["scores"].get("efficiency"),
            score_reproducibility=judge_result["scores"].get("reproducibility"),
            score_safety_hygiene=judge_result["scores"].get("safety_hygiene"),
            score_overall=judge_result["scores"].get("overall")
        )
        
        db.add(qa_result)
        
        # Update trace status
        trace.status = TraceStatus.VALIDATED
        db.commit()
        
        logger.info(f"QA complete for trace {trace_id}")
        
        return {
            "trace_id": trace_id,
            "validation": validation_result,
            "judge": judge_result
        }
    
    except Exception as e:
        logger.error(f"Error in QA for trace {trace_id}: {e}", exc_info=True)
        
        # Mark trace as failed
        if db:
            trace = db.query(Trace).filter(Trace.id == trace_id).first()
            if trace:
                trace.status = TraceStatus.FAILED
                db.commit()
        
        raise
    
    finally:
        db.close()


def load_trace_document(trace_uri: str) -> dict:
    """Load trace document from storage."""
    # Parse URI
    parts = trace_uri.split("/", 4)
    bucket = parts[3]
    object_name = parts[4]
    
    # Download
    data = download_blob(bucket, object_name)
    return json.loads(data.decode("utf-8"))


def run_validation(trace_id: str, trace_doc: dict, db: Session) -> dict:
    """
    Run validation by executing tests in Docker.
    
    Args:
        trace_id: Trace identifier
        trace_doc: Trace document
        db: Database session
    
    Returns:
        Validation results
    """
    # Find workspace snapshot
    artifacts_data = trace_doc.get("artifacts") or {}
    snapshot_ref = artifacts_data.get("final_workspace_snapshot") if artifacts_data else None
    
    if not snapshot_ref:
        logger.warning(f"No workspace snapshot found for trace {trace_id}")
        return {
            "tests_passed": None,
            "framework": "pytest",
            "error": "No workspace snapshot provided"
        }
    
    # Download workspace snapshot
    snapshot_uri = snapshot_ref["uri"]
    parts = snapshot_uri.split("/", 4)
    bucket = parts[3]
    object_name = parts[4]
    
    workspace_data = download_blob(bucket, object_name)
    
    # Run tests
    runner = TestRunner()
    result = runner.run_pytest(workspace_data)
    
    # Store validation log
    if result.get("stdout") or result.get("stderr"):
        log_content = f"=== STDOUT ===\n{result.get('stdout', '')}\n\n=== STDERR ===\n{result.get('stderr', '')}"
        log_id = str(uuid4())
        object_name = f"{trace_id}/validation_log_{log_id}.txt"
        log_uri, _, _ = upload_blob(
            BUCKET_ARTIFACTS,
            object_name,
            log_content.encode("utf-8"),
            content_type="text/plain"
        )
        result["log_uri"] = log_uri
    
    return result


def run_judge(trace_doc: dict) -> dict:
    """
    Run LLM judge evaluation.
    
    Args:
        trace_doc: Trace document
    
    Returns:
        Judge results with scores and feedback
    """
    # Build prompt
    prompt = build_judge_prompt(trace_doc)
    
    # Run judge
    judge = LLMJudge()
    result = judge.evaluate(prompt)
    
    return result

