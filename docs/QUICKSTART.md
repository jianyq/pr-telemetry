# Quick Start Guide

Get PR Telemetry up and running in 5 minutes!

## Prerequisites

- Docker Desktop installed and running
- Python 3.11+ (for running the example)
- 8GB+ RAM available

## Step 1: Start Services (30 seconds)

```bash
# Start all services
docker-compose up -d

# Wait for startup (check when ready)
curl http://localhost:8000/healthz
```

✅ When you see `{"status": "healthy", ...}` you're ready!

## Step 2: Run Example (2 minutes)

```bash
# Install Python client library
pip install httpx

# Run the E2E example
python examples/submit_example.py
```

## What the Example Does

1. ✅ Creates a trace for fixing a buggy calculator
2. ✅ Uploads 10 events (edits, commands, tests, rationales)
3. ✅ Completes the trace
4. ✅ Triggers QA validation (runs tests in Docker)
5. ✅ Gets LLM judge scores

## Expected Output

```
============================================================
PR Telemetry E2E Example
============================================================

[1/5] Creating trace...
✓ Created trace: trace-abc123

[2/5] Uploading event chunks...
  ✓ 3 events added
  ✓ 3 events added
  ✓ 4 events added

[3/5] Creating and uploading workspace snapshot...
  ✓ Final chunk uploaded

[4/5] Completing trace...
✓ Trace completed
  Total events: 10

[5/5] Waiting for QA validation and judging...
✓ QA Complete!

  Validation Results:
    Tests Passed: True
    Passed: 5
    Failed: 0
    Runtime: 2.34s

  Judge Evaluation:
    Overall Score: 3.5/5
    Feedback: The developer demonstrated a systematic 
    approach to debugging...

============================================================
```

## Step 3: Explore

### View in Browser

- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (admin/admin)

### Use the API

```bash
# Create a trace
curl -X POST http://localhost:8000/v1/traces \
  -H "Authorization: Bearer dev_token_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "user-123",
    "task_id": "task-456",
    "task_title": "Fix bug in function"
  }'

# Get a trace
curl http://localhost:8000/v1/traces/{trace_id} \
  -H "Authorization: Bearer dev_token_12345"
```

### View Logs

```bash
# All logs
docker-compose logs -f

# Just API
docker-compose logs -f api

# Just worker
docker-compose logs -f worker
```

## Step 4: Stop When Done

```bash
# Stop services (keeps data)
docker-compose stop

# Or remove everything
docker-compose down -v
```

## Using Makefile (Optional)

If you have `make` installed:

```bash
make start    # Start services
make example  # Run example
make logs     # View logs
make clean    # Remove everything
```

## Troubleshooting

### "Connection refused"
Wait 30-60 seconds for services to fully start, then try again.

### "Port already in use"
Stop conflicting services or edit `docker-compose.yml` to use different ports.

### "Docker not found"
Install Docker Desktop: https://www.docker.com/products/docker-desktop

### Example script fails
```bash
# Check API is running
curl http://localhost:8000/healthz

# Check logs
docker-compose logs api
```

## Next Steps

- Read the full [README.md](README.md) for architecture details
- Explore the [API documentation](http://localhost:8000/docs)
- Check the [example repo](examples/repo-buggy/) to understand the bug
- Review [example trace chunks](examples/sample-trace-chunks/)
- Integrate with your IDE workflow

## Need Help?

- Check [README.md](README.md) troubleshooting section
- View logs: `docker-compose logs`
- Open an issue on GitHub

---

**You're all set! 🎉**

The PR Telemetry system is now capturing, validating, and analyzing bug-fixing traces.

