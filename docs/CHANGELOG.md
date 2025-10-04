# Changelog

All notable changes to the PR Telemetry Trace project.

## [1.0.0] - 2025-10-04

### Added - Initial Release (Stage 1)

#### Core Infrastructure
- FastAPI-based REST API server with 5 endpoints
- PostgreSQL database for metadata storage
- MinIO/S3-compatible object storage for artifacts
- Redis + Celery for asynchronous task queue
- Docker Compose orchestration for all services
- Alembic database migration system

#### API Endpoints
- `POST /v1/traces` - Create new trace
- `POST /v1/traces/{id}/events:ingest` - Upload event chunks
- `POST /v1/traces/{id}/complete` - Finalize trace
- `GET /v1/traces/{id}` - Retrieve trace with QA results
- `GET /healthz` and `GET /readyz` - Health checks

#### Data Models
- Complete Pydantic schema matching JSON spec v1.0
- 5 event types: file_edit, cmd_run, test_run, commit, rationale_note
- BlobRef for external artifact storage
- Structured rationale fields (plan, hypothesis, observation, decision, next_step)
- Metrics computation (duration, edit counts, file churn)

#### Ingestion Pipeline
- Incremental chunk-based ingestion
- Event hash chain (HMAC-SHA256) for integrity
- Idempotency key support (24-hour deduplication)
- Automatic artifact extraction and storage
- Event sequence validation

#### QA Validation
- Docker-based test runner for pytest
- Security-hardened containers:
  - Network isolation (`--network=none`)
  - Non-root user execution
  - Resource limits (CPU, memory, PIDs)
  - Dropped Linux capabilities
- Dynamic Dockerfile generation
- Test result parsing and storage
- Log capture to S3

#### LLM Judge
- Multi-dimensional evaluation rubric (6 dimensions)
- OpenAI API integration
- Mock mode for testing without API key
- Rubric dimensions:
  - Problem Understanding (20%)
  - Causal Linking (25%)
  - Experiment Design (20%)
  - Efficiency (15%)
  - Reproducibility (10%)
  - Safety & Hygiene (10%)
- Weighted overall score computation
- Structured feedback generation

#### Examples & Documentation
- Buggy calculator example repository
- 3 sample trace chunks (10 events total)
- Automated E2E submission script
- Comprehensive README with architecture details
- Quick start guide (QUICKSTART.md)
- Complete schema reference (SCHEMA.md)
- Project summary document
- Makefile for common operations
- MIT license

#### Security
- Bearer token authentication
- Upload token per trace
- Idempotency key tracking
- Container sandboxing
- Resource limits on test execution
- Secret redaction infrastructure (placeholder)

#### Developer Experience
- Type-safe Pydantic models
- Automatic API documentation (Swagger/OpenAPI)
- Structured logging throughout
- Health and readiness endpoints
- Clear error messages
- One-command startup

### Technical Details

**Dependencies:**
- Python 3.11
- FastAPI 0.104
- Pydantic 2.5
- SQLAlchemy 2.0
- Celery 5.3
- PostgreSQL 15
- Redis 7
- MinIO (latest)
- Docker

**Database Tables:**
- `traces` - Main trace records
- `trace_chunks` - Raw uploaded chunks
- `artifacts` - Stored blobs
- `qa_results` - Validation and judge results
- `idempotency_keys` - Request deduplication

**Storage Buckets:**
- `pr-telemetry-artifacts` - Command outputs, logs, snapshots
- `pr-telemetry-chunks` - Raw chunk uploads
- `pr-telemetry-traces` - Finalized trace documents

### Known Limitations

- Single-node deployment only
- pytest-only test runner
- Mock LLM judge by default
- Basic authentication (dev token)
- No UI for visualization
- Limited to Python repos in validation

### Future Work (Stage 2)

See PROJECT_SUMMARY.md for planned enhancements.

---

## Release Format

This project uses [Semantic Versioning](https://semver.org/).

- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible functionality
- **PATCH** version for backward-compatible bug fixes

### Types of Changes

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for removed features
- **Fixed** for bug fixes
- **Security** for vulnerability fixes

