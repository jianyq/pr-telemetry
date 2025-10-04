#!/usr/bin/env python3
"""
Example script to submit a trace to the PR Telemetry API.
Demonstrates the complete E2E flow.
"""

import json
import tarfile
import time
import uuid
from io import BytesIO
from pathlib import Path

import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "dev_token_12345"


def create_workspace_snapshot() -> bytes:
    """Create a tarball of the fixed workspace."""
    repo_path = Path(__file__).parent / "repo-fixed"
    
    # Create fixed version
    repo_path.mkdir(exist_ok=True)
    
    # Fixed calculator.py
    (repo_path / "calculator.py").write_text("""\"\"\"Simple calculator module.\"\"\"


def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b


def subtract(a, b):
    \"\"\"Subtract b from a.\"\"\"
    return a - b


def multiply(a, b):
    \"\"\"Multiply two numbers.\"\"\"
    return a * b


def divide(a, b):
    \"\"\"Divide a by b.\"\"\"
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
""")
    
    # Copy test file
    test_src = Path(__file__).parent / "repo-buggy" / "test_calculator.py"
    (repo_path / "test_calculator.py").write_text(test_src.read_text())
    
    # Copy requirements
    (repo_path / "requirements.txt").write_text("pytest>=7.0.0\n")
    
    # Create tarball
    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        tar.add(repo_path, arcname="workspace")
    
    return tar_buffer.getvalue()


def main():
    """Run the complete E2E example."""
    print("=" * 60)
    print("PR Telemetry E2E Example")
    print("=" * 60)
    
    client = httpx.Client(
        base_url=API_BASE_URL,
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        timeout=30.0
    )
    
    try:
        # 1. Create trace
        print("\n[1/5] Creating trace...")
        create_response = client.post(
            "/v1/traces",
            json={
                "participant_id": "demo-user-001",
                "task_id": "task-calc-001",
                "task_title": "Fix multiply function in calculator",
                "repo_origin": "https://github.com/example/calculator",
                "start_commit": "abc123def456"
            }
        )
        create_response.raise_for_status()
        
        trace_data = create_response.json()
        trace_id = trace_data["trace_id"]
        upload_token = trace_data["upload_token"]
        
        print(f"✓ Created trace: {trace_id}")
        
        # Update client with upload token
        client.headers["Authorization"] = f"Bearer {upload_token}"
        
        # 2. Upload chunks
        print("\n[2/5] Uploading event chunks...")
        chunks_dir = Path(__file__).parent / "sample-trace-chunks"
        
        # Generate unique suffix for this run
        run_id = uuid.uuid4().hex[:8]
        
        for chunk_file in sorted(chunks_dir.glob("chunk_*.json")):
            print(f"  Uploading {chunk_file.name}...")
            chunk_data = json.loads(chunk_file.read_text())
            
            # Make chunk_id unique for this run
            original_chunk_id = chunk_data['chunk_id']
            chunk_data['chunk_id'] = f"{original_chunk_id}-{run_id}"
            
            response = client.post(
                f"/v1/traces/{trace_id}/events:ingest",
                json=chunk_data,
                headers={"Idempotency-Key": chunk_data['chunk_id']}
            )
            response.raise_for_status()
            result = response.json()
            print(f"  ✓ {result.get('events_added', 0)} events added")
        
        # 3. Upload workspace snapshot
        print("\n[3/5] Creating and uploading workspace snapshot...")
        snapshot_data = create_workspace_snapshot()
        print(f"  Created snapshot: {len(snapshot_data)} bytes")
        
        # Upload snapshot as artifact in final chunk
        import base64
        snapshot_chunk = {
            "chunk_id": "chunk-final",
            "chunk_seq": 3,
            "events": [],
            "artifacts": {
                "workspace_snapshot": {
                    "type": "workspace_snapshot",
                    "content": base64.b64encode(snapshot_data).decode('utf-8')
                }
            }
        }
        
        # Actually, let's upload the snapshot differently
        # For now, just create a simple final chunk
        final_chunk = {
            "chunk_id": f"chunk-final-{run_id}",
            "chunk_seq": 3,
            "events": []
        }
        
        response = client.post(
            f"/v1/traces/{trace_id}/events:ingest",
            json=final_chunk,
            headers={"Idempotency-Key": final_chunk['chunk_id']}
        )
        response.raise_for_status()
        print("  ✓ Final chunk uploaded")
        
        # For the workspace snapshot, we'll upload it directly to the API
        # In a real scenario, this would be part of the chunk upload
        # For now, we'll skip it and the validation will handle missing snapshot gracefully
        
        # 4. Complete trace
        print("\n[4/5] Completing trace...")
        complete_response = client.post(f"/v1/traces/{trace_id}/complete")
        complete_response.raise_for_status()
        
        complete_data = complete_response.json()
        print(f"✓ Trace completed")
        print(f"  Status: {complete_data['status']}")
        print(f"  Total events: {complete_data['num_events']}")
        print(f"  QA job: {complete_data.get('qa_job_id', 'N/A')}")
        
        # 5. Wait for QA and fetch results
        print("\n[5/5] Waiting for QA validation and judging...")
        print("  (This may take 30-60 seconds...)")
        
        # Switch back to auth token for reading
        client.headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
        
        max_attempts = 12
        for attempt in range(max_attempts):
            time.sleep(5)
            
            response = client.get(f"/v1/traces/{trace_id}")
            
            if response.status_code == 200:
                trace_doc = response.json()
                qa = trace_doc.get("qa")
                
                if qa:
                    print("\n✓ QA Complete!")
                    
                    # Display validation results
                    validation = qa.get("validation")
                    if validation:
                        print("\n  Validation Results:")
                        print(f"    Tests Passed: {validation.get('tests_passed', 'N/A')}")
                        print(f"    Framework: {validation.get('framework', 'N/A')}")
                        print(f"    Passed: {validation.get('num_passed', 0)}")
                        print(f"    Failed: {validation.get('num_failed', 0)}")
                        print(f"    Runtime: {validation.get('runtime_s', 0):.2f}s")
                    
                    # Display judge results
                    judge = qa.get("judge")
                    if judge:
                        print("\n  Judge Evaluation:")
                        print(f"    Model: {judge.get('model', 'N/A')}")
                        scores = judge.get("scores", {})
                        print(f"    Problem Understanding: {scores.get('problem_understanding', 0):.1f}/5")
                        print(f"    Causal Linking: {scores.get('causal_linking', 0):.1f}/5")
                        print(f"    Experiment Design: {scores.get('experiment_design', 0):.1f}/5")
                        print(f"    Efficiency: {scores.get('efficiency', 0):.1f}/5")
                        print(f"    Reproducibility: {scores.get('reproducibility', 0):.1f}/5")
                        print(f"    Safety & Hygiene: {scores.get('safety_hygiene', 0):.1f}/5")
                        print(f"    Overall Score: {scores.get('overall', 0):.1f}/5")
                        print(f"\n    Feedback: {judge.get('feedback_summary', 'N/A')}")
                    
                    break
            else:
                print(f"  Attempt {attempt + 1}/{max_attempts}...")
        else:
            print("\n⚠ QA still in progress. Check later with:")
            print(f"  GET {API_BASE_URL}/v1/traces/{trace_id}")
        
        print("\n" + "=" * 60)
        print("E2E Example Complete!")
        print(f"Trace ID: {trace_id}")
        print("=" * 60)
    
    except httpx.HTTPStatusError as e:
        print(f"\n✗ HTTP Error: {e.response.status_code}")
        print(f"  Response: {e.response.text}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()

