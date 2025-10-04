# PR Telemetry Trace System

A comprehensive system for capturing, validating, and analyzing developer bug-fixing sessions. This system enables researchers to collect high-quality training data for AI models by recording complete developer workflows from initial bug report to verified fix.

## 🎯 Overview

The PR Telemetry system captures:
- **Developer actions**: File edits, commands, test runs, commits
- **Reasoning traces**: Structured rationales (plans, hypotheses, observations, decisions)
- **Artifacts**: Command outputs, test reports, workspace snapshots
- **QA validation**: Automated test execution in isolated containers
- **LLM evaluation**: AI-based scoring using a multi-dimensional rubric

## 🏗️ Architecture

```
┌─────────────────┐
│   Developer     │
│   (IDE Client)  │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────────────────────────┐
│                   FastAPI Server                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   Routes     │  │  Ingestion   │  │  Storage  │ │
│  │  /v1/traces  │─▶│   Service    │─▶│  (MinIO)  │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────┬───────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │   PostgreSQL    │
         │   (Metadata)    │
         └─────────────────┘
                  │
         ┌────────┴────────┐
         │   Redis Queue   │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │  Celery Worker  │
         │  ┌───────────┐  │
         │  │  Docker   │  │
         │  │   Test    │  │
         │  │  Runner   │  │
         │  └───────────┘  │
         │  ┌───────────┐  │
         │  │    LLM    │  │
         │  │   Judge   │  │
         │  └───────────┘  │
         └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for running examples locally)
- 8GB+ RAM recommended
- (Optional) OpenAI API key for real LLM evaluation

### 1. Start the System

```bash
# Clone and navigate to the project
cd pr-telemetry

# Start all services
docker-compose up -d

# Check service health (wait ~30 seconds for startup)
curl http://localhost:8000/healthz
```

Expected output:
```json
{"status": "healthy", "timestamp": "2025-10-04T..."}
```

### 2. Run the E2E Example

```bash
# Install Python dependencies for the example script
pip install httpx

# Run the example
python examples/submit_example.py
```

This will:
1. ✅ Create a new trace
2. ✅ Upload 3 chunks of events (10 events total)
3. ✅ Upload workspace snapshot
4. ✅ Complete the trace and trigger QA
5. ✅ Wait for validation and judge results

### 3. Configure LLM Judge (Optional)

By default, the system uses a mock LLM judge. To use real OpenAI evaluation:

**Update docker-compose.yml**:
```yaml
# Edit docker-compose.yml, worker environment:
OPENAI_API_KEY: your-api-key-here
```

Then restart:
```bash
docker-compose restart worker
```

**Check LLM Status**:
```bash
docker-compose logs worker | grep "LLM Judge"
# Should see: "Initializing LLM Judge with model: gpt-4o-mini"
```

📄 See [docs/LLM_JUDGE_STATUS.md](docs/LLM_JUDGE_STATUS.md) for detailed information about the LLM integration.

### 4. View Logs

```bash
# API logs
docker-compose logs -f api

# Worker logs
docker-compose logs -f worker

# All logs
docker-compose logs -f
```

### 5. Stop the System

```bash
docker-compose down

# To also remove volumes (data)
docker-compose down -v
```

## 📚 API Reference

### Base URL
```
http://localhost:8000
```

### Authentication
All endpoints require a Bearer token:
```
Authorization: Bearer dev_token_12345
```

### Endpoints

#### 1. Create Trace
```http
POST /v1/traces
Content-Type: application/json
Authorization: Bearer dev_token_12345

{
  "participant_id": "user-123",
  "task_id": "task-456",
  "task_title": "Fix failing test",
  "repo_origin": "https://github.com/example/repo",
  "start_commit": "abc123"
}
```

**Response:**
```json
{
  "trace_id": "trace-xxxxx",
  "upload_token": "yyyyyyy",
  "message": "Trace created successfully"
}
```

#### 2. Ingest Events
```http
POST /v1/traces/{trace_id}/events:ingest
Content-Type: application/json
Authorization: Bearer {upload_token}
Idempotency-Key: chunk-001

{
  "chunk_id": "chunk-001",
  "chunk_seq": 0,
  "events": [
    {
      "id": "event-001",
      "seq": 0,
      "ts_client_s": 1696435200.0,
      "ts_server_s": 1696435200.0,
      "type": "file_edit",
      "file_path": "src/main.py",
      "diff_unified": "...",
      "buffer_hash_after": "abc123..."
    }
  ],
  "artifacts": {
    "stdout": {
      "type": "stdout",
      "event_id": "event-001",
      "content": "test output..."
    }
  }
}
```

#### 3. Complete Trace
```http
POST /v1/traces/{trace_id}/complete
Authorization: Bearer {upload_token}
```

**Response:**
```json
{
  "status": "success",
  "trace_id": "trace-xxxxx",
  "final_uri": "http://...",
  "num_events": 10,
  "qa_job_id": "celery-task-id"
}
```

#### 4. Get Trace
```http
GET /v1/traces/{trace_id}
Authorization: Bearer dev_token_12345
```

**Response:** Full trace document with QA results (if ready)

## 📋 Event Types

### File Edit
```json
{
  "type": "file_edit",
  "file_path": "src/main.py",
  "language": "python",
  "diff_unified": "--- a/src/main.py\n+++ b/src/main.py\n...",
  "buffer_hash_after": "sha256..."
}
```

### Command Run
```json
{
  "type": "cmd_run",
  "cmd": "pytest test_main.py",
  "cwd": "/workspace",
  "exit_code": 0
}
```

### Test Run
```json
{
  "type": "test_run",
  "framework": "pytest",
  "num_passed": 5,
  "num_failed": 0,
  "failed_tests": []
}
```

### Commit
```json
{
  "type": "commit",
  "sha": "abc123",
  "message": "Fix bug in multiply function",
  "diff_unified": "..."
}
```

### Rationale Note
```json
{
  "type": "rationale_note",
  "structured": {
    "plan": "Run tests to identify failing test",
    "hypothesis": "The multiply function is adding instead of multiplying",
    "observation": "Test shows 2*3 returns 5 instead of 6",
    "decision": "Change + to * operator",
    "next_step": "Re-run tests to verify fix"
  }
}
```

## 🎯 QA Pipeline

### 1. Validation (Docker Test Runner)

The system automatically:
- Extracts workspace snapshot
- Builds Docker image with workspace
- Runs tests in isolated container with:
  - ❌ No network access (`--network=none`)
  - 👤 Non-root user
  - 💾 1GB memory limit
  - ⏱️ 10-minute timeout
  - 🔒 Security restrictions (no-new-privileges, dropped capabilities)

### 2. LLM Judge

Evaluates the trace on 6 dimensions (0-5 scale):

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Problem Understanding** | 20% | Clear grasp of failure modes and requirements |
| **Causal Linking** | 25% | Connects observations → hypotheses → edits |
| **Experiment Design** | 20% | Sound testing strategy, isolation, validation |
| **Efficiency** | 15% | Minimal churn, appropriate edit locality |
| **Reproducibility** | 10% | Actions clearly replayable from trace |
| **Safety & Hygiene** | 10% | No dangerous commands, proper secret handling |

**Overall Score**: Weighted average of all dimensions

## 🔧 Configuration

### Environment Variables

Create a `.env` file (or use `.env.example`):

```bash
# Database
DATABASE_URL=postgresql://telemetry:password@postgres:5432/pr_telemetry

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO/S3
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# Auth
AUTH_TOKEN=dev_token_12345

# LLM Judge (optional)
OPENAI_API_KEY=sk-...   # or "mock" for testing

# Logging
LOG_LEVEL=INFO
```

## 🧪 Development

### Project Structure

```
pr-telemetry/
├── api/                      # FastAPI application
│   ├── main.py              # API routes and endpoints
│   ├── schemas/             # Pydantic models
│   │   └── trace_v1.py      # Trace schema v1.0
│   ├── db/                  # Database layer
│   │   ├── models.py        # SQLAlchemy models
│   │   └── session.py       # DB session management
│   ├── services/            # Business logic
│   │   ├── ingest.py        # Event ingestion
│   │   ├── finalize.py      # Trace finalization
│   │   └── hash_chain.py    # Integrity verification
│   └── storage/             # Storage layer
│       └── minio_client.py  # MinIO/S3 client
├── worker/                   # Celery worker
│   ├── tasks.py             # Celery tasks
│   ├── qa/                  # QA validation
│   │   └── runner.py        # Docker test runner
│   └── judge/               # LLM judge
│       ├── prompt.py        # Rubric and prompts
│       └── llm_judge.py     # Judge implementation
├── examples/                 # Example data
│   ├── repo-buggy/          # Buggy calculator repo
│   ├── sample-trace-chunks/ # Example trace chunks
│   └── submit_example.py    # E2E demo script
├── infra/                    # Infrastructure
│   ├── Dockerfile.api       # API container
│   └── Dockerfile.worker    # Worker container
├── alembic/                  # Database migrations
├── docker-compose.yml        # Service orchestration
└── requirements.txt          # Python dependencies
```

### Running Tests

```bash
# Unit tests (example)
pytest tests/

# Integration test via E2E example
python examples/submit_example.py
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 🔍 Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Restart services
docker-compose restart

# Full reset
docker-compose down -v
docker-compose up -d
```

### MinIO buckets not created

```bash
# Manually create buckets
docker-compose exec minio mc alias set myminio http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb myminio/pr-telemetry-artifacts
docker-compose exec minio mc mb myminio/pr-telemetry-chunks
docker-compose exec minio mc mb myminio/pr-telemetry-traces
```

### Database connection issues

```bash
# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready -U telemetry

# Connect to database
docker-compose exec postgres psql -U telemetry -d pr_telemetry
```

### Worker not processing tasks

```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# Restart worker
docker-compose restart worker

# Check worker logs
docker-compose logs -f worker
```

## 📊 Example Output

After running the E2E example, you'll see:

```
============================================================
PR Telemetry E2E Example
============================================================

[1/5] Creating trace...
✓ Created trace: trace-abc123def456

[2/5] Uploading event chunks...
  Uploading chunk_01.json...
  ✓ 3 events added
  Uploading chunk_02.json...
  ✓ 3 events added
  Uploading chunk_03.json...
  ✓ 4 events added

[3/5] Creating and uploading workspace snapshot...
  Created snapshot: 2048 bytes
  ✓ Final chunk uploaded

[4/5] Completing trace...
✓ Trace completed
  Status: success
  Total events: 10
  QA job: celery-task-xyz

[5/5] Waiting for QA validation and judging...
  (This may take 30-60 seconds...)

✓ QA Complete!

  Validation Results:
    Tests Passed: True
    Framework: pytest
    Passed: 5
    Failed: 0
    Runtime: 2.34s

  Judge Evaluation:
    Model: mock
    Problem Understanding: 3.5/5
    Causal Linking: 3.0/5
    Experiment Design: 3.5/5
    Efficiency: 3.0/5
    Reproducibility: 4.0/5
    Safety & Hygiene: 4.5/5
    Overall Score: 3.5/5

    Feedback: The developer demonstrated a systematic approach 
    to debugging. Good reproducibility and safety practices. 
    Could improve efficiency by reducing redundant test runs.

============================================================
E2E Example Complete!
Trace ID: trace-abc123def456
============================================================
```

## 🔐 Security Considerations

### Current Implementation (MVP)
- ✅ Bearer token authentication
- ✅ Idempotency keys (24h)
- ✅ Docker container isolation
- ✅ Resource limits (CPU, memory, PIDs)
- ✅ Network isolation (`--network=none`)
- ✅ Non-root user in containers
- ✅ Security options (`no-new-privileges`, dropped capabilities)

### Production Recommendations
- 🔒 Use HTTPS/TLS
- 🔒 JWT with short expiration
- 🔒 Rate limiting
- 🔒 Advanced sandboxing (gVisor, Firecracker)
- 🔒 Secret scanning and redaction
- 🔒 Audit logging
- 🔒 RBAC for multi-tenancy

## 📈 Scalability

### Current Limits (Single Node)
- ~100 concurrent traces
- ~1000 events/second ingestion
- ~10 validation jobs/minute

### Scaling Options
1. **Horizontal API scaling**: Add more API containers behind load balancer
2. **Worker scaling**: Add more Celery workers
3. **Database**: PostgreSQL read replicas
4. **Storage**: Switch to AWS S3/CloudFront
5. **Queue**: Redis Cluster or RabbitMQ

## 🗺️ Roadmap

### Stage 1 (Current) ✅
- ✅ Core ingestion pipeline
- ✅ Event schema v1.0
- ✅ Docker-based validation
- ✅ LLM judge
- ✅ E2E example

### Stage 2 (Future)
- [ ] Multi-language test runners (Jest, JUnit, Go)
- [ ] Keystroke-level edit tracking
- [ ] IDE plugins (VSCode, JetBrains)
- [ ] Web UI for trace visualization
- [ ] Analytics dashboard
- [ ] Coverage and static analysis integration
- [ ] Multi-model judge ensemble

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📚 Documentation

For detailed documentation, see the [`docs/`](docs/) folder:

### Core Documentation
- **[STAGE1_PROJECT_PLAN.md](docs/STAGE1_PROJECT_PLAN.md)** - Original project plan with clarifying questions, schema design, and architecture
- **[QUICKSTART.md](docs/QUICKSTART.md)** - Quick setup guide for getting started
- **[SCHEMA.md](docs/SCHEMA.md)** - Complete JSON schema reference with examples

### Implementation Details
- **[PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md)** - High-level overview of the system
- **[TESTING.md](docs/TESTING.md)** - Comprehensive testing guide with examples
- **[GET_STARTED.md](docs/GET_STARTED.md)** - Step-by-step guide for new users

### LLM Judge
- **[LLM_JUDGE_STATUS.md](docs/LLM_JUDGE_STATUS.md)** - Current status and implementation details
- **[LLM_IMPLEMENTATION_SUMMARY.md](docs/LLM_IMPLEMENTATION_SUMMARY.md)** - Complete implementation overview

### Project Management
- **[CHANGELOG.md](docs/CHANGELOG.md)** - Version history and changes
- **[REVIEW_AND_NEXT_STEPS.md](docs/REVIEW_AND_NEXT_STEPS.md)** - Project review and future improvements

## 📞 Support

For questions or issues:
- Open a GitHub issue
- Check the troubleshooting section above
- Review API logs: `docker-compose logs api`

---

**Built with**: FastAPI • Celery • PostgreSQL • MinIO • Docker • Python 3.11
