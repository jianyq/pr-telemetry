# Testing & Verification Guide

Complete guide to verify the PR Telemetry system is working correctly.

## Pre-Deployment Checklist

### System Requirements

- [ ] Docker Desktop installed and running
- [ ] Docker Compose v2+ available
- [ ] Python 3.11+ installed (for example script)
- [ ] At least 8GB RAM available
- [ ] Ports 5432, 6379, 8000, 9000, 9001 available

Check with:
```bash
docker --version          # Should be 20.10+
docker-compose --version  # Should be 2.0+
python3 --version        # Should be 3.11+
```

## Deployment Tests

### 1. Service Startup (60 seconds)

```bash
# Start all services
docker-compose up -d

# Wait for startup
sleep 30

# Check all containers are running
docker-compose ps
```

**Expected Output:**
```
NAME                      STATUS        PORTS
pr-telemetry-api          Up            0.0.0.0:8000->8000/tcp
pr-telemetry-worker       Up            
pr-telemetry-postgres     Up (healthy)  0.0.0.0:5432->5432/tcp
pr-telemetry-redis        Up (healthy)  0.0.0.0:6379->6379/tcp
pr-telemetry-minio        Up (healthy)  0.0.0.0:9000-9001->9000-9001/tcp
```

### 2. Health Checks (5 seconds)

```bash
# API health
curl -s http://localhost:8000/healthz | jq

# API readiness
curl -s http://localhost:8000/readyz | jq

# Redis
docker-compose exec redis redis-cli ping

# PostgreSQL
docker-compose exec postgres pg_isready -U telemetry

# MinIO
curl -s http://localhost:9000/minio/health/live
```

**Expected:**
- API health: `{"status": "healthy", ...}`
- API ready: `{"status": "ready", "database": "connected", ...}`
- Redis: `PONG`
- PostgreSQL: `accepting connections`
- MinIO: HTTP 200

### 3. Database Initialization (10 seconds)

```bash
# Check tables exist
docker-compose exec postgres psql -U telemetry -d pr_telemetry -c "\dt"
```

**Expected Tables:**
- `traces`
- `trace_chunks`
- `artifacts`
- `qa_results`
- `idempotency_keys`
- `alembic_version`

### 4. Storage Buckets (5 seconds)

```bash
# List buckets
docker-compose exec minio mc ls myminio/
```

**Expected Buckets:**
- `pr-telemetry-artifacts/`
- `pr-telemetry-chunks/`
- `pr-telemetry-traces/`

## API Tests

### Test 1: Root Endpoint

```bash
curl -s http://localhost:8000/ | jq
```

**Expected:**
```json
{
  "name": "PR Telemetry API",
  "version": "1.0.0",
  "endpoints": { ... }
}
```

### Test 2: Create Trace

```bash
curl -X POST http://localhost:8000/v1/traces \
  -H "Authorization: Bearer dev_token_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "test-user-001",
    "task_id": "test-task-001",
    "task_title": "Test trace creation",
    "repo_origin": "https://github.com/test/repo",
    "start_commit": "abc123"
  }' | jq
```

**Expected:**
```json
{
  "trace_id": "trace-xxxxx",
  "upload_token": "xxxxxx",
  "message": "Trace created successfully"
}
```

**Save these values:**
```bash
TRACE_ID="<trace_id from response>"
UPLOAD_TOKEN="<upload_token from response>"
```

### Test 3: Ingest Events

```bash
curl -X POST http://localhost:8000/v1/traces/$TRACE_ID/events:ingest \
  -H "Authorization: Bearer $UPLOAD_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-chunk-001" \
  -d '{
    "chunk_id": "test-chunk-001",
    "chunk_seq": 0,
    "events": [
      {
        "id": "test-event-001",
        "seq": 0,
        "ts_client_s": 1696435200.0,
        "ts_server_s": 1696435200.0,
        "type": "rationale_note",
        "structured": {
          "plan": "Test event ingestion"
        }
      }
    ]
  }' | jq
```

**Expected:**
```json
{
  "status": "success",
  "chunk_id": "test-chunk-001",
  "events_added": 1,
  "total_events": 1
}
```

### Test 4: Get Trace (Before Completion)

```bash
curl -s http://localhost:8000/v1/traces/$TRACE_ID \
  -H "Authorization: Bearer dev_token_12345" | jq
```

**Expected:**
```json
{
  "status": "ingesting",
  "message": "Trace not yet finalized",
  "num_events": 1
}
```

### Test 5: Complete Trace

```bash
curl -X POST http://localhost:8000/v1/traces/$TRACE_ID/complete \
  -H "Authorization: Bearer $UPLOAD_TOKEN" | jq
```

**Expected:**
```json
{
  "status": "success",
  "trace_id": "trace-xxxxx",
  "num_events": 1,
  "qa_job_id": "..."
}
```

## E2E Integration Test

### Run Full Example

```bash
# Install dependencies
pip install httpx

# Run example
python examples/submit_example.py
```

**Expected Output:**
```
============================================================
PR Telemetry E2E Example
============================================================

[1/5] Creating trace...
✓ Created trace: trace-xxxxx

[2/5] Uploading event chunks...
  ✓ 3 events added
  ✓ 3 events added
  ✓ 4 events added

[3/5] Creating and uploading workspace snapshot...
  ✓ Final chunk uploaded

[4/5] Completing trace...
✓ Trace completed

[5/5] Waiting for QA validation and judging...
✓ QA Complete!

  Validation Results:
    Tests Passed: [True/False]
    Framework: pytest
    ...

  Judge Evaluation:
    Overall Score: X.X/5
    ...

============================================================
E2E Example Complete!
============================================================
```

**Validation Criteria:**
- [ ] All 5 steps complete without errors
- [ ] Trace ID returned
- [ ] Events uploaded (10 total)
- [ ] QA completes within 60 seconds
- [ ] Validation results present
- [ ] Judge scores present (6 dimensions + overall)
- [ ] Feedback summary non-empty

## Worker Tests

### Test 1: Celery Status

```bash
# Check worker is running
docker-compose exec worker celery -A worker.tasks inspect active
```

**Expected:**
```json
{"celery@worker": []}  // Empty or active tasks
```

### Test 2: Task Execution

After running E2E example, check logs:

```bash
docker-compose logs worker | grep "Starting QA for trace"
docker-compose logs worker | grep "QA complete for trace"
```

**Expected:**
- See "Starting QA for trace: trace-xxxxx"
- See "QA complete for trace trace-xxxxx"
- No errors or exceptions

## Storage Tests

### Test 1: MinIO Objects

```bash
# List stored objects
docker-compose exec minio mc ls -r myminio/pr-telemetry-chunks/
docker-compose exec minio mc ls -r myminio/pr-telemetry-traces/
docker-compose exec minio mc ls -r myminio/pr-telemetry-artifacts/
```

**Expected:** Objects present for each trace

### Test 2: Database Records

```bash
# Check trace records
docker-compose exec postgres psql -U telemetry -d pr_telemetry -c \
  "SELECT id, status, num_events FROM traces LIMIT 5;"

# Check QA results
docker-compose exec postgres psql -U telemetry -d pr_telemetry -c \
  "SELECT trace_id, validation_tests_passed, score_overall FROM qa_results LIMIT 5;"
```

## Performance Tests

### Load Test (Simple)

```bash
# Create 10 traces concurrently
for i in {1..10}; do
  (curl -X POST http://localhost:8000/v1/traces \
    -H "Authorization: Bearer dev_token_12345" \
    -H "Content-Type: application/json" \
    -d "{
      \"participant_id\": \"user-$i\",
      \"task_id\": \"task-$i\",
      \"task_title\": \"Load test trace $i\"
    }" &)
done
wait
```

**Expected:**
- All requests succeed (HTTP 200)
- Response times < 1 second
- No errors in logs

### Concurrent Ingestion

```bash
# Measure ingestion rate
time python examples/submit_example.py
```

**Expected:**
- Completes in < 5 seconds (ingestion only)
- QA completes in 30-60 seconds total

## Failure Tests

### Test 1: Invalid Token

```bash
curl -X POST http://localhost:8000/v1/traces \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" \
  -d '{"participant_id":"test","task_id":"test","task_title":"test"}'
```

**Expected:** HTTP 401 Unauthorized

### Test 2: Duplicate Chunk (Idempotency)

```bash
# Upload same chunk twice with same idempotency key
# (Use commands from API Test 3)
```

**Expected:** 
- Second request returns same response
- Only 1 event added to trace

### Test 3: Invalid Event Schema

```bash
curl -X POST http://localhost:8000/v1/traces/$TRACE_ID/events:ingest \
  -H "Authorization: Bearer $UPLOAD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_id": "bad-chunk",
    "chunk_seq": 999,
    "events": [
      {
        "id": "bad-event",
        "seq": 999,
        "type": "invalid_type"
      }
    ]
  }'
```

**Expected:** HTTP 422 Validation Error

## Cleanup Tests

### Restart Persistence

```bash
# Stop services
docker-compose stop

# Start again
docker-compose start

# Verify data persists
curl -s http://localhost:8000/v1/traces/$TRACE_ID \
  -H "Authorization: Bearer dev_token_12345" | jq
```

**Expected:** Previous trace data still accessible

### Full Reset

```bash
# Remove everything
docker-compose down -v

# Start fresh
docker-compose up -d
sleep 30

# Verify empty
docker-compose exec postgres psql -U telemetry -d pr_telemetry -c \
  "SELECT COUNT(*) FROM traces;"
```

**Expected:** `count = 0`

## Monitoring & Logs

### API Logs

```bash
# Follow API logs
docker-compose logs -f api

# Search for errors
docker-compose logs api | grep -i error
```

### Worker Logs

```bash
# Follow worker logs
docker-compose logs -f worker

# Check for task failures
docker-compose logs worker | grep -i "error\|exception\|failed"
```

### Database Logs

```bash
docker-compose logs postgres | grep -i error
```

## Automated Test Script

Save as `tests/verify_deployment.sh`:

```bash
#!/bin/bash
set -e

echo "Running deployment verification tests..."

# Test 1: Health
echo -n "Testing health endpoint... "
curl -sf http://localhost:8000/healthz > /dev/null && echo "✓" || echo "✗"

# Test 2: Readiness
echo -n "Testing readiness endpoint... "
curl -sf http://localhost:8000/readyz > /dev/null && echo "✓" || echo "✗"

# Test 3: Create trace
echo -n "Testing trace creation... "
RESPONSE=$(curl -sf -X POST http://localhost:8000/v1/traces \
  -H "Authorization: Bearer dev_token_12345" \
  -H "Content-Type: application/json" \
  -d '{"participant_id":"test","task_id":"test","task_title":"test"}')
TRACE_ID=$(echo $RESPONSE | jq -r '.trace_id')
[[ -n "$TRACE_ID" ]] && echo "✓" || echo "✗"

echo ""
echo "Verification complete!"
```

## Success Criteria

All tests must pass:

- [ ] All services start and report healthy
- [ ] Database tables created
- [ ] Storage buckets exist
- [ ] API endpoints respond correctly
- [ ] Event ingestion works
- [ ] Trace finalization succeeds
- [ ] Worker processes QA tasks
- [ ] Judge produces scores
- [ ] E2E example completes successfully
- [ ] Data persists across restarts
- [ ] Logs show no errors
- [ ] Performance within acceptable limits

## Troubleshooting Common Issues

**Issue:** Services won't start
- **Solution:** Check Docker Desktop is running, ports are free

**Issue:** API returns 503
- **Solution:** Wait 30-60 seconds for startup

**Issue:** Worker not processing
- **Solution:** Check Redis connection, restart worker

**Issue:** Judge returns mock scores
- **Solution:** Set `OPENAI_API_KEY` environment variable

**Issue:** Tests fail in Docker
- **Solution:** Check Docker socket mounted correctly

---

**All tests passing?** ✅ Your PR Telemetry system is ready for production use!

