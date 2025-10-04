#!/usr/bin/env python3
"""
Failed debugging E2E example - demonstrates an incomplete bug fix.
This trace shows a developer who:
- Attempts to fix a bug but doesn't fully understand the problem
- Makes changes that don't fix the issue
- Adds debug logging without fixing the root cause
- Ends without a successful resolution
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

def submit_failed_trace():
    """Submit a trace showing failed debugging attempt."""
    print("=" * 60)
    print("PR Telemetry - Failed Debugging Example")
    print("=" * 60)
    print()
    print("Scenario: Unsuccessful attempt to fix authentication bug")
    print("Demonstrates:")
    print("  • Incomplete problem analysis")
    print("  • Changes that don't fix the issue")
    print("  • Debug logging instead of proper fix")
    print("  • No successful resolution")
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
            "task_id": "BUG-9999",
            "task_title": "Fix intermittent authentication token expiration issue",
            "participant_id": "developer-003",
            "repo_origin": "https://github.com/example/auth-service",
            "start_commit": "xyz9876543210"
        })
        response.raise_for_status()
        result = response.json()
        trace_id = result["trace_id"]
        upload_token = result["upload_token"]
        print(f"✓ Created trace: {trace_id}")
        
        # Save original token
        original_token = AUTH_TOKEN
        
        # Update client with upload token
        client.headers["Authorization"] = f"Bearer {upload_token}"
        
        # 2. Upload chunks
        print("\n[2/5] Uploading event chunks...")
        chunks_dir = Path(__file__).parent / "failed-trace-chunks"
        
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
        
        # 3. Complete trace (even though bug not fixed!)
        print("\n[3/5] Completing trace...")
        response = client.post(f"/v1/traces/{trace_id}/complete")
        response.raise_for_status()
        result = response.json()
        print(f"✓ Trace completed (bug NOT fixed)")
        print(f"  Status: {result['status']}")
        print(f"  Total events: {result['num_events']}")
        print(f"  QA job: {result.get('qa_job_id', 'N/A')}")
        
        # 4. Wait for QA
        print("\n[4/5] Waiting for QA validation and judging...")
        print("  (AI Judge will evaluate this failed attempt...)")
        print()
        
        # Switch back to original token
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
                    print("  Judge Evaluation (Failed Attempt):")
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
        print("Failed Debugging Example Complete!")
        print(f"Trace ID: {trace_id}")
        print("=" * 60)
        print()
        print("This trace demonstrates:")
        print("  ✗ Incomplete problem understanding")
        print("  ✗ Changes that don't address root cause")
        print("  ✗ Debug statements left in production code")
        print("  ✗ No successful test results")
        print("  ✗ No commit (work incomplete)")
        print()
        print("Expected AI Judge to give LOW scores for:")
        print("  • Problem Understanding")
        print("  • Causal Linking")
        print("  • Experiment Design")
        print("  • Safety & Hygiene (debug print statements)")
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
    submit_failed_trace()

