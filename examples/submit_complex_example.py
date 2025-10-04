#!/usr/bin/env python3
"""
Complex E2E example demonstrating a multi-file bug fix scenario.
This trace shows a more realistic debugging session with:
- Multiple file edits
- Iterative problem solving
- Test-driven debugging
- Detailed rationale notes
"""

import json
import sys
import time
import uuid
from pathlib import Path

import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "dev_token_12345"

def submit_complex_trace():
    """Submit a complex trace with multiple debugging iterations."""
    print("=" * 60)
    print("PR Telemetry - Complex E2E Example")
    print("=" * 60)
    print()
    print("Scenario: Multi-file bug fix for order calculation")
    print("Features:")
    print("  • 24 events across 4 chunks")
    print("  • 3 file edits (order_service, database_helper, tests)")
    print("  • Multiple test iterations")
    print("  • Detailed problem-solving rationale")
    print()
    
    client = httpx.Client(
        base_url=API_BASE_URL,
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        timeout=30.0
    )
    
    try:
        # 1. Create trace
        print("[1/5] Creating trace...")
        response = client.post("/v1/traces", json={
            "task_id": "ISSUE-5678",
            "task_title": "Fix 500 error when creating orders with multiple items",
            "participant_id": "developer-002",
            "repo_origin": "https://github.com/example/ecommerce-api",
            "start_commit": "def4567890abcdef"
        })
        response.raise_for_status()
        result = response.json()
        trace_id = result["trace_id"]
        upload_token = result["upload_token"]
        print(f"✓ Created trace: {trace_id}")
        
        # Save original token for later queries
        original_token = AUTH_TOKEN
        
        # Update client with upload token for uploading
        client.headers["Authorization"] = f"Bearer {upload_token}"
        
        # 2. Upload chunks
        print("\n[2/5] Uploading event chunks...")
        chunks_dir = Path(__file__).parent / "complex-trace-chunks"
        
        # Generate unique run ID
        run_id = uuid.uuid4().hex[:8]
        
        chunk_files = sorted(chunks_dir.glob("chunk_*.json"))
        for chunk_file in chunk_files:
            print(f"  Uploading {chunk_file.name}...")
            chunk_data = json.loads(chunk_file.read_text())
            
            # Make chunk_id unique
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
        
        # 3. Complete trace
        print("\n[3/5] Completing trace...")
        response = client.post(f"/v1/traces/{trace_id}/complete")
        response.raise_for_status()
        result = response.json()
        print(f"✓ Trace completed")
        print(f"  Status: {result['status']}")
        print(f"  Total events: {result['num_events']}")
        print(f"  QA job: {result.get('qa_job_id', 'N/A')}")
        
        # 4. Wait for QA
        print("\n[4/5] Waiting for QA validation and judging...")
        print("  (This may take 30-60 seconds...)")
        print()
        
        # Switch back to original token for querying
        client.headers["Authorization"] = f"Bearer {original_token}"
        
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(2)
            response = client.get(f"/v1/traces/{trace_id}")
            response.raise_for_status()
            trace = response.json()
            
            if trace.get('qa'):
                print("✓ QA Complete!")
                print()
                
                # Display results
                judge = trace['qa'].get('judge', {})
                if judge:
                    print("  Judge Evaluation:")
                    print(f"    Model: {judge.get('model', 'N/A')}")
                    scores = judge.get('scores', {})
                    print(f"    Problem Understanding: {scores.get('problem_understanding', 0):.1f}/5")
                    print(f"    Causal Linking: {scores.get('causal_linking', 0):.1f}/5")
                    print(f"    Experiment Design: {scores.get('experiment_design', 0):.1f}/5")
                    print(f"    Efficiency: {scores.get('efficiency', 0):.1f}/5")
                    print(f"    Reproducibility: {scores.get('reproducibility', 0):.1f}/5")
                    print(f"    Safety & Hygiene: {scores.get('safety_hygiene', 0):.1f}/5")
                    print(f"    Overall Score: {scores.get('overall', 0):.1f}/5")
                    print()
                    print(f"    Feedback: {judge.get('feedback_summary', 'N/A')}")
                break
        else:
            print("⚠ QA still in progress. Check later with:")
            print(f"  GET {API_BASE_URL}/v1/traces/{trace_id}")
        
        # 5. Summary
        print()
        print("=" * 60)
        print("Complex E2E Example Complete!")
        print(f"Trace ID: {trace_id}")
        print("=" * 60)
        print()
        print("This trace demonstrates:")
        print("  ✓ Multi-file bug fixing (3 files edited)")
        print("  ✓ Iterative debugging (4 test runs)")
        print("  ✓ Problem analysis and hypothesis testing")
        print("  ✓ Test-driven development workflow")
        print("  ✓ Comprehensive commit message")
        print()
        print("View details with:")
        print(f"  python view_trace.py {trace_id}")
        print()
        
        return trace_id
        
    except httpx.HTTPStatusError as e:
        print(f"\n✗ HTTP Error: {e.response.status_code}")
        print(f"  Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    submit_complex_trace()

