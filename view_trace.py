#!/usr/bin/env python3
"""Convenient script to view trace information"""
import sys
import json
import httpx

API_BASE = "http://localhost:8000"
TOKEN = "dev_token_12345"

def view_trace(trace_id):
    """View detailed trace information"""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        response = httpx.get(f"{API_BASE}/v1/traces/{trace_id}", headers=headers)
        response.raise_for_status()
        trace = response.json()
        
        print(f"\n{'='*60}")
        print(f"📋 Trace: {trace['trace_id']}")
        print(f"{'='*60}\n")
        
        # Task information
        print(f"🎯 Task: {trace['task']['title']}")
        print(f"👤 Participant: {trace['session']['participant_id']}")
        print(f"📅 Created: {trace['created_at']}")
        
        # Metrics
        metrics = trace.get('metrics', {})
        print(f"\n📊 Metrics:")
        print(f"  ⏱️  Duration: {metrics.get('duration_s', 0):.1f}s")
        print(f"  📝 Total Events: {metrics.get('num_events', 0)}")
        print(f"  ✏️  File Edits: {metrics.get('num_edits', 0)}")
        print(f"  💻 Commands: {metrics.get('num_cmds', 0)}")
        print(f"  🧪 Test Runs: {metrics.get('num_test_runs', 0)}")
        
        # Event summary
        events = trace.get('events', [])
        print(f"\n📋 Event Timeline ({len(events)} events):")
        for i, event in enumerate(events[:10], 1):
            etype = event['type']
            emoji = {'rationale_note': '💡', 'cmd_run': '💻', 'test_run': '🧪', 
                     'file_edit': '✏️', 'commit': '📦'}.get(etype, '📌')
            
            if etype == 'file_edit':
                print(f"  {i}. {emoji} Edit file: {event['file_path']}")
            elif etype == 'cmd_run':
                status = '✅' if event['exit_code'] == 0 else '❌'
                print(f"  {i}. {emoji} Command: {event['cmd']} {status}")
            elif etype == 'test_run':
                print(f"  {i}. {emoji} Tests: {event['num_passed']} passed, {event['num_failed']} failed")
            elif etype == 'rationale_note':
                structured = event.get('structured', {})
                text = (structured.get('plan') or structured.get('hypothesis') or 
                       structured.get('observation') or structured.get('decision') or 'Rationale')
                print(f"  {i}. {emoji} {text[:50]}")
            elif etype == 'commit':
                print(f"  {i}. {emoji} Commit: {event['message'][:50]}")
        
        if len(events) > 10:
            print(f"  ... and {len(events)-10} more events")
        
        # QA Results
        qa = trace.get('qa')
        print(f"\n🎯 QA Results:")
        if qa is None:
            print("  ⏳ QA validation not yet completed")
        else:
            validation = qa.get('validation', {})
            if validation:
                tests_passed = validation.get('tests_passed')
                if tests_passed:
                    print(f"  ✅ Test Validation: PASSED")
                else:
                    print(f"  ❌ Test Validation: FAILED")
                print(f"     Framework: {validation.get('framework', 'N/A')}")
                print(f"     Passed: {validation.get('num_passed', 0)}, Failed: {validation.get('num_failed', 0)}")
                print(f"     Runtime: {validation.get('runtime_s', 0):.2f}s")
            
            judge = qa.get('judge', {})
            if judge:
                scores = judge.get('scores', {})
                print(f"\n  🤖 AI Judge (model: {judge.get('model', 'N/A')}):")
                print(f"     Problem Understanding: {scores.get('problem_understanding', 0):.1f}/5")
                print(f"     Causal Linking: {scores.get('causal_linking', 0):.1f}/5")
                print(f"     Experiment Design: {scores.get('experiment_design', 0):.1f}/5")
                print(f"     Efficiency: {scores.get('efficiency', 0):.1f}/5")
                print(f"     Reproducibility: {scores.get('reproducibility', 0):.1f}/5")
                print(f"     Safety & Hygiene: {scores.get('safety_hygiene', 0):.1f}/5")
                print(f"     ⭐ Overall Score: {scores.get('overall', 0):.1f}/5")
                
                feedback = judge.get('feedback_summary')
                if feedback:
                    print(f"\n  💬 Feedback: {feedback}")
        
        print(f"\n{'='*60}\n")
        
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python view_trace.py <trace_id>")
        print("Example: python view_trace.py trace-a0dfa2b87929")
        sys.exit(1)
    
    view_trace(sys.argv[1])
