# PR Telemetry Trace Schema v1.0

Complete reference for the trace JSON schema.

## Top-Level Structure

```json
{
  "trace_version": "1.0",
  "trace_id": "trace-xxxxx",
  "session": { /* Session metadata */ },
  "task": { /* Task description */ },
  "repo": { /* Repository info */ },
  "environment": { /* Dev environment */ },
  "events": [ /* Array of events */ ],
  "artifacts": { /* Final artifacts */ },
  "metrics": { /* Summary metrics */ },
  "qa": { /* QA results */ },
  "integrity": { /* Integrity data */ },
  "created_at": "2025-10-04T12:00:00Z",
  "completed_at": "2025-10-04T12:15:00Z"
}
```

## Session

Metadata about the participant and their consent settings.

```json
{
  "participant_id": "user-123",
  "role": "human_dev",
  "consent": {
    "rationales": true,
    "commands": true,
    "snapshots": true
  },
  "client_clock": {
    "tz": "America/New_York",
    "start_unix_s": 1696435200.0
  }
}
```

## Task

Description of the bug-fixing task.

```json
{
  "id": "task-456",
  "title": "Fix multiply function",
  "description": "The multiply function returns incorrect results",
  "known_failing_tests": [
    "test_multiply"
  ]
}
```

## Repository

Information about the codebase.

```json
{
  "origin": "https://github.com/example/repo",
  "branch": "main",
  "start_commit": "abc123def456",
  "language_stats": [
    {"lang": "python", "ratio": 0.8},
    {"lang": "markdown", "ratio": 0.2}
  ]
}
```

## Events

### Base Event Fields

All events share these fields:

```json
{
  "id": "event-001",
  "seq": 0,
  "ts_client_s": 1696435200.0,
  "ts_server_s": 1696435200.1,
  "type": "file_edit"
}
```

### File Edit Event

```json
{
  "type": "file_edit",
  "file_path": "src/calculator.py",
  "language": "python",
  "diff_unified": "--- a/src/calculator.py\n+++ b/src/calculator.py\n@@ -10,7 +10,7 @@\n-    return a + b\n+    return a * b",
  "buffer_hash_before": "abc123...",
  "buffer_hash_after": "def456...",
  "edit_bytes": 123
}
```

### Command Run Event

```json
{
  "type": "cmd_run",
  "cmd": "pytest test_calculator.py",
  "cwd": "/workspace",
  "env_redacted": false,
  "exit_code": 0,
  "stdout_ref": {
    "uri": "s3://bucket/trace-xxx/stdout.txt",
    "sha256": "abc123...",
    "size_bytes": 1024
  },
  "stderr_ref": { /* Same structure */ }
}
```

### Test Run Event

```json
{
  "type": "test_run",
  "framework": "pytest",
  "selection": "test_calculator.py::test_multiply",
  "num_passed": 5,
  "num_failed": 0,
  "failed_tests": [],
  "report_ref": {
    "uri": "s3://bucket/trace-xxx/report.json",
    "sha256": "def456...",
    "size_bytes": 2048
  }
}
```

### Commit Event

```json
{
  "type": "commit",
  "sha": "a1b2c3d4",
  "parent_sha": "abc123...",
  "message": "Fix multiply function",
  "diff_unified": "..."
}
```

### Rationale Note Event

```json
{
  "type": "rationale_note",
  "structured": {
    "plan": "Run tests to identify the failing test",
    "hypothesis": "The function is adding instead of multiplying",
    "observation": "Test shows 2*3=5 instead of 6",
    "decision": "Change operator from + to *",
    "next_step": "Re-run tests to verify"
  },
  "freeform": "Optional free-form notes..."
}
```

## Artifacts

References to stored binary/large data.

```json
{
  "final_workspace_snapshot": {
    "uri": "s3://bucket/trace-xxx/workspace.tar.gz",
    "sha256": "abc123...",
    "size_bytes": 1048576
  },
  "final_patch_unified": "--- a/calculator.py\n+++ b/calculator.py\n..."
}
```

## Metrics

Computed summary statistics.

```json
{
  "duration_s": 125.5,
  "num_events": 10,
  "num_edits": 3,
  "num_cmds": 4,
  "num_test_runs": 2,
  "files_touched": 2,
  "edit_churn_lines": 15
}
```

## QA

Quality assurance results from validation and judging.

### Validation

```json
{
  "validation": {
    "tests_passed": true,
    "framework": "pytest",
    "num_passed": 5,
    "num_failed": 0,
    "runtime_s": 2.34,
    "container_image": "pr-telemetry-test:xxx",
    "log": {
      "uri": "s3://bucket/trace-xxx/validation.log",
      "sha256": "def456...",
      "size_bytes": 4096
    }
  }
}
```

### Judge

```json
{
  "judge": {
    "model": "gpt-4",
    "model_version": "gpt-4-0613",
    "rubric_version": "1.0",
    "scores": {
      "problem_understanding": 3.5,
      "causal_linking": 3.0,
      "experiment_design": 3.5,
      "efficiency": 3.0,
      "reproducibility": 4.0,
      "safety_hygiene": 4.5,
      "overall": 3.5
    },
    "feedback_summary": "The developer demonstrated a systematic approach..."
  }
}
```

### Judge Rubric (0-5 scale)

| Dimension | Weight | Description |
|-----------|--------|-------------|
| problem_understanding | 20% | Clear understanding of failure modes |
| causal_linking | 25% | Connects observations → hypotheses → fixes |
| experiment_design | 20% | Sound testing strategy |
| efficiency | 15% | Minimal churn, appropriate locality |
| reproducibility | 10% | Actions clearly replayable |
| safety_hygiene | 10% | No dangerous commands, proper secrets |

**Overall**: Weighted average of all dimensions

## Integrity

Cryptographic integrity verification.

```json
{
  "event_hash_chain": "final_hmac_hash...",
  "schema_hash": "schema_version_hash..."
}
```

The `event_hash_chain` is computed as:

```python
hash_n = HMAC-SHA256(hash_{n-1} + event_n_json)
```

Starting with `hash_0 = HMAC-SHA256(event_0_json)`.

## Data Types

### Timestamps

- **ts_client_s**: Client-side timestamp (Unix seconds, float)
- **ts_server_s**: Server receive timestamp (Unix seconds, float)
- **created_at/completed_at**: ISO 8601 datetime strings

### BlobRef

Reference to stored binary data:

```json
{
  "uri": "s3://bucket/key or http://...",
  "sha256": "64-char hex string",
  "size_bytes": 1024
}
```

### Unified Diff Format

Standard unified diff (GNU diff):

```diff
--- a/file.py
+++ b/file.py
@@ -10,7 +10,7 @@ def function():
-    old line
+    new line
```

## Validation Rules

### Event Ordering

1. Events MUST be ordered by `seq` (ascending)
2. `seq` values MUST be non-negative integers
3. `seq` values SHOULD be contiguous (gaps allowed but discouraged)
4. Each `id` MUST be unique within the trace

### Required Fields

**Minimal trace**:
```json
{
  "trace_version": "1.0",
  "trace_id": "...",
  "session": {
    "participant_id": "...",
    "consent": {"rationales": true, "commands": true, "snapshots": true}
  },
  "task": {
    "id": "...",
    "title": "..."
  },
  "repo": {
    "origin": "...",
    "start_commit": "..."
  },
  "events": [],
  "created_at": "..."
}
```

## Example Complete Trace

See `examples/sample-trace-chunks/` for a real example that you can submit to the API.

## Schema Versioning

Current version: **1.0**

Future versions will:
- Increment major version for breaking changes
- Increment minor version for backward-compatible additions
- Support multiple versions concurrently

---

For implementation details, see `api/schemas/trace_v1.py`.

