# Stage 1: Project Plan & Specification
## PR Telemetry Trace System

**Author**: Development Team  
**Date**: October 4, 2025  
**Purpose**: Define architecture and implementation strategy for capturing developer bug-fixing traces

---

## 1. Clarifying Questions & Assumptions

### Critical Questions for the Researcher

#### Q1: **What level of granularity is needed for edit capture?**
- Keystroke-level (every character typed)?
- On-save diffs (changes when file is saved)?
- Commit-level diffs (final changes only)?

**ASSUMPTION**: We'll capture **on-save diffs** as a middle ground. This provides:
- Sufficient detail to understand the developer's thought process
- Manageable data volume (vs. keystroke-level)
- More context than commit-only (shows iteration)
- Easier to replay and analyze

#### Q2: **How critical is precise timing information?**
- Millisecond precision between all actions?
- Second-level timestamps sufficient?
- Need to account for clock drift/timezone issues?

**ASSUMPTION**: **Second-level timestamps** with dual recording:
- Client-side timestamps (relative timing)
- Server-side timestamps (absolute verification)
- This handles clock drift while preserving action sequences

#### Q3: **What test frameworks and languages must we support initially?**
- Python (pytest, unittest)?
- JavaScript (Jest, Mocha)?
- Java (JUnit)?
- Go, Rust, other languages?

**ASSUMPTION**: Start with **Python/pytest** as MVP because:
- Well-defined test output format
- Easy to parse results programmatically
- Large research community uses Python
- Can extend to other frameworks later with pluggable interface

#### Q4: **What type of "reasoning" or "rationale" data is most valuable?**
- Raw LLM chain-of-thought?
- Structured fields (plan, hypothesis, observation)?
- Free-form developer notes?
- Automatic inference from actions?

**ASSUMPTION**: Prefer **structured rationale** with optional free-form:
- Reduces PII/compliance risk vs. raw chain-of-thought
- More analyzable for ML training
- Fields: plan, hypothesis, observation, decision, next_step
- Optional free-form field for flexibility

#### Q5: **How should we define "verified fix"?**
- All tests pass?
- Specific failing test now passes?
- Include linter checks?
- Require coverage thresholds?

**ASSUMPTION**: **All tests pass in clean container** as core requirement:
- Run in isolated Docker environment
- Network disabled for reproducibility
- Optional: lint checks as bonus data
- This is unambiguous and automatable

### Additional Key Assumptions

**A6: Data Governance**
- Users provide explicit consent (captured in metadata)
- Server-side secret redaction (API keys, passwords)
- 90-day retention by default
- Access controlled via bearer tokens

**A7: Artifact Storage**
- Large data (logs, snapshots) stored externally (S3/MinIO)
- Events reference artifacts via URI + hash
- Keeps event stream lightweight

**A8: Scalability Expectations**
- Initial: 10-100 developers
- Support for 1000+ traces/day
- Can scale horizontally later

---

## 2. Proposed JSON Schema

### Design Philosophy

The schema prioritizes:
1. **Trainability**: Complete information for ML model learning
2. **Integrity**: Tamper-evident with hash chains
3. **Scalability**: Chunked ingestion, external artifacts
4. **Privacy**: Explicit consent flags, redaction hooks
5. **Extensibility**: Versioned, typed events

### Top-Level Structure

```json
{
  "trace_version": "1.0",
  "trace_id": "trace-xxxxx",
  "session": { },
  "task": { },
  "repo": { },
  "environment": { },
  "events": [ ],
  "artifacts": { },
  "metrics": { },
  "qa": { },
  "integrity": { },
  "created_at": "ISO8601",
  "completed_at": "ISO8601"
}
```

### Key Design Decisions

#### **Event Structure**
```json
{
  "id": "uuid",
  "seq": 0,
  "ts_client_s": 1696435200.0,
  "ts_server_s": 1696435200.1,
  "type": "file_edit"
}
```

**Rationale**:
- `id`: Globally unique, prevents duplication
- `seq`: Ordering within trace, allows gap detection
- Dual timestamps: Client for relative timing, server for verification
- `type`: Discriminator for event union types

#### **Event Types**

**1. File Edit**
```json
{
  "type": "file_edit",
  "file_path": "relative/path",
  "language": "python",
  "diff_unified": "...",
  "buffer_hash_after": "sha256"
}
```

**Why unified diffs?**
- Standard format, widely supported
- Human and machine readable
- Compact representation of changes
- Easy to apply/reverse

**2. Command Run**
```json
{
  "type": "cmd_run",
  "cmd": "pytest test.py",
  "exit_code": 0,
  "stdout_ref": { "uri": "...", "sha256": "..." }
}
```

**Why reference outputs?**
- Avoid bloating events with large outputs
- Separate storage optimized for blobs
- Allows streaming without loading everything

**3. Test Run**
```json
{
  "type": "test_run",
  "framework": "pytest",
  "num_passed": 5,
  "num_failed": 0,
  "failed_tests": ["test_name"]
}
```

**Why separate from command?**
- Structured test results for analysis
- Framework-agnostic representation
- Easy to query "which tests failed when?"

**4. Rationale Note**
```json
{
  "type": "rationale_note",
  "structured": {
    "plan": "...",
    "hypothesis": "...",
    "observation": "...",
    "decision": "...",
    "next_step": "..."
  }
}
```

**Why structured fields?**
- Safer than free-form (less PII risk)
- Directly maps to debugging process
- Easier to train models on specific reasoning types
- Can still include freeform if consented

#### **QA Section**

```json
{
  "qa": {
    "validation": {
      "tests_passed": true,
      "framework": "pytest",
      "runtime_s": 2.5
    },
    "judge": {
      "model": "gpt-4",
      "scores": {
        "problem_understanding": 3.5,
        "causal_linking": 3.0,
        "overall": 3.4
      },
      "feedback_summary": "..."
    }
  }
}
```

**Why two-stage QA?**
1. **Validation**: Objective, deterministic
2. **Judge**: Subjective, evaluates process quality
3. Together: Complete picture of solution quality

**Rubric Dimensions** (0-5 scale):
- Problem Understanding (20%)
- Causal Linking (25%)
- Experiment Design (20%)
- Efficiency (15%)
- Reproducibility (10%)
- Safety & Hygiene (10%)

**Why these?** They map to core debugging skills:
- Understanding the problem
- Reasoning from observations to fixes
- Good testing practices
- Not wasting effort
- Can be replayed
- Safe coding practices

#### **Integrity**

```json
{
  "integrity": {
    "event_hash_chain": "hmac_sha256_final",
    "schema_hash": "sha256_of_schema_v1"
  }
}
```

**Why hash chain?**
- Tamper evidence: any change breaks chain
- Efficient: incremental computation
- Standard: HMAC-SHA256 widely supported
- Formula: `hash_n = HMAC(secret, hash_{n-1} + event_n)`

---

## 3. High-Level Technical Plan

### Architecture Overview

```
[IDE Client] 
    ↓ HTTPS/JSON
[FastAPI Ingestion]
    ↓
[PostgreSQL] ← metadata
[MinIO/S3]   ← blobs
[Redis]      ← task queue
    ↓
[Celery Worker]
    ├─ Docker Test Runner
    └─ LLM Judge
```

### Tech Stack Choices

#### **API Layer: FastAPI + Pydantic**

**Why FastAPI?**
- Native async support (important for ingestion load)
- Automatic OpenAPI docs
- Pydantic validation (type-safe)
- Fast performance
- Modern Python ecosystem

**Why Pydantic?**
- Runtime validation of complex schemas
- Type hints = documentation
- JSON serialization built-in
- Easy to extend

#### **Database: PostgreSQL**

**Why Postgres?**
- JSONB support (flexible metadata storage)
- Strong consistency guarantees
- Well-understood operational model
- Good Python drivers (asyncpg)
- Not NoSQL: we need transactions, foreign keys

**What we store**:
- Trace metadata (status, timestamps)
- Chunk tracking
- QA results
- Idempotency keys

**What we DON'T store**: 
- Event arrays (too large)
- Artifacts (blobs)

#### **Object Storage: MinIO (S3-compatible)**

**Why MinIO?**
- S3-compatible API (easy to swap to AWS later)
- Self-hosted (good for MVP)
- Excellent for large blobs
- Built-in integrity checking

**Bucket strategy**:
- `pr-telemetry-chunks`: Raw uploaded chunks
- `pr-telemetry-artifacts`: Command outputs, logs
- `pr-telemetry-traces`: Finalized JSON documents

#### **Queue: Celery + Redis**

**Why Celery?**
- Mature, battle-tested
- Good monitoring tools
- Retry logic built-in
- Python-native

**Why Redis?**
- Fast, simple
- Good enough for MVP
- Easy to deploy
- Can upgrade to RabbitMQ if needed

**Task types**:
- Trace finalization
- Test validation
- LLM judging

#### **Container Runtime: Docker**

**Why Docker?**
- Industry standard
- Good isolation
- Resource limits
- Easy to reproduce

**Security constraints**:
- `--network=none`
- Non-root user
- CPU/memory limits
- Read-only where possible
- Dropped capabilities

---

## 4. Scope & Trade-offs

### MVP Features (MUST HAVE)

#### Core Ingestion
✅ Create trace endpoint  
✅ Incremental chunk upload  
✅ Event validation against schema  
✅ Idempotency support  
✅ Artifact storage with refs  

#### Data Integrity
✅ Hash chain computation  
✅ Event sequence validation  
✅ Blob integrity (SHA-256)  

#### QA Pipeline
✅ Finalize trace (assemble chunks)  
✅ Docker test runner (pytest)  
✅ Parse test results  
✅ LLM judge with rubric  
✅ Store QA results  

#### API
✅ Health checks  
✅ Bearer token auth  
✅ Get finalized trace  
✅ OpenAPI documentation  

#### Deployment
✅ Docker Compose setup  
✅ Database migrations  
✅ One-command startup  
✅ Example trace + repo  

### Nice-to-Have (DESCOPED for MVP)

#### ❌ Multi-Language Support
- **Deferred**: Jest, JUnit, Go test
- **Why**: Each requires custom parser
- **Later**: Pluggable runner interface

#### ❌ Keystroke-Level Edits
- **Deferred**: Too much data, privacy concerns
- **Why**: On-save is sufficient for MVP
- **Later**: Optional detailed mode

#### ❌ Advanced Sandboxing
- **Deferred**: gVisor, Firecracker
- **Why**: Docker sufficient for MVP
- **Later**: If security review requires

#### ❌ Web Search/Navigation Events
- **Deferred**: Complex to capture accurately
- **Why**: Not critical for core debugging loop
- **Later**: Browser extension integration

#### ❌ Analytics Dashboard
- **Deferred**: Query API directly for now
- **Why**: Researcher can build custom viz
- **Later**: Pre-built dashboard if common patterns emerge

#### ❌ Coverage/Static Analysis Integration
- **Deferred**: Adds complexity
- **Why**: Test pass/fail is core validation
- **Later**: Optional enrichment

#### ❌ Multi-Tenant UI
- **Deferred**: API-first approach
- **Why**: Researchers will script access
- **Later**: If non-technical users need access

#### ❌ Fine-Grained RBAC
- **Deferred**: Simple bearer tokens
- **Why**: Small team, trusted environment
- **Later**: JWT with roles if scaling

### Trade-off Decisions

#### **Decision 1: Chunked vs. Streaming Ingestion**

**Chosen**: Chunked (batch uploads)

**Why?**
- Simpler client implementation
- Natural checkpointing
- Easier to resume on failure
- Idempotency straightforward

**Trade-off**: Slightly higher latency vs. true streaming

#### **Decision 2: Structured vs. Free-form Rationales**

**Chosen**: Structured with optional free-form

**Why?**
- Lower privacy risk (no raw LLM outputs with PII)
- More analyzable (discrete fields)
- Still flexible (free-form available)

**Trade-off**: Less "natural" than pure chain-of-thought

#### **Decision 3: Single vs. Multi-Model Judge**

**Chosen**: Single strong model for MVP

**Why?**
- Simpler implementation
- Lower cost
- One model with fixed prompt easier to debug

**Trade-off**: No ensemble voting, potential bias

#### **Decision 4: Python-Only vs. Multi-Language**

**Chosen**: Python/pytest only initially

**Why?**
- 80% of research repos use Python
- Can prove full pipeline works
- Other languages follow same pattern

**Trade-off**: Limits initial adoption

#### **Decision 5: On-Save vs. Keystroke Edits**

**Chosen**: On-save diffs

**Why?**
- 10-100x less data
- Still shows iteration
- Easier to reason about
- Less noisy

**Trade-off**: Lose some granularity of thought process

---

## 5. Implementation Phases

### Phase 1: Foundation (Week 1)
- Set up FastAPI skeleton
- Define Pydantic models
- Database schema + migrations
- MinIO integration
- Health checks

### Phase 2: Ingestion (Week 1-2)
- Create trace endpoint
- Chunk ingestion with validation
- Hash chain computation
- Artifact upload
- Idempotency

### Phase 3: QA Pipeline (Week 2)
- Celery worker setup
- Docker test runner
- Test result parsing
- LLM judge integration
- Result storage

### Phase 4: E2E Example (Week 2)
- Create buggy repo
- Generate sample trace
- Submission script
- Verify QA works end-to-end

### Phase 5: Documentation (Week 2-3)
- API documentation
- Schema reference
- Setup guide
- Troubleshooting guide

---

## 6. Success Criteria

### MVP is successful if:

1. ✅ **Complete Workflow**: Trace uploaded → validated → judged → retrieved
2. ✅ **Data Quality**: Schema validates, hash chain verifies
3. ✅ **Reproducible**: Tests run in clean container match local results
4. ✅ **Documented**: Researcher can deploy and use without help
5. ✅ **Secure**: Tests run in isolated sandbox
6. ✅ **Fast Enough**: Ingestion <100ms/event, QA <5min/trace

### Acceptance Test

```bash
# 1. Start system
docker-compose up -d

# 2. Submit example trace
python examples/submit_example.py

# 3. Verify results
curl localhost:8000/v1/traces/{trace_id}

# Expected: 
# - tests_passed: true
# - judge scores present
# - all events captured
```

---

## 7. Risks & Mitigations

### Risk 1: Untrusted Code Execution
**Mitigation**: 
- Docker isolation
- Network disabled
- Resource limits
- Non-root user
- Timeout enforcement

### Risk 2: Data Volume at Scale
**Mitigation**:
- Chunked ingestion
- External blob storage
- Compression
- Configurable retention

### Risk 3: LLM Judge Variance
**Mitigation**:
- Fixed model + prompt
- Temperature = 0.2
- Version tracking
- Optional ensemble (later)

### Risk 4: Clock Drift/Timing Issues
**Mitigation**:
- Dual timestamps
- Server-side recording
- Sequence numbers

### Risk 5: Schema Evolution
**Mitigation**:
- Version field in schema
- Support multiple versions
- Migration tooling

---

## 8. Future Enhancements (Post-MVP)

### Short-term (Months 2-3)
- Jest/JavaScript support
- Coverage integration
- Web dashboard
- Batch export API

### Medium-term (Months 4-6)
- JUnit/Java support
- Horizontal scaling
- Advanced analytics
- IDE plugins (VSCode)

### Long-term (Year 1+)
- Multi-model judge ensemble
- Keystroke-level optional mode
- Federated learning support
- Benchmark dataset publication

---

## 9. Open Questions for Stage 2

Before implementation, clarify:

1. **Storage Costs**: Is S3 budget approved or use MinIO long-term?
2. **Judge Model**: Which specific model(s) to use? (GPT-4, Claude, open-source?)
3. **Access Control**: Who needs API access? How are tokens managed?
4. **Monitoring**: What metrics matter most? (latency, volume, errors?)
5. **Data Export**: Need batch export? What format? (JSONL, Parquet?)

---

## Summary

This plan outlines a **pragmatic, production-ready MVP** that:
- Captures complete debugging sessions
- Validates fixes automatically
- Evaluates developer reasoning
- Maintains data integrity
- Scales to research needs

**Key Principles**:
- 🎯 **Start simple**: Python/pytest only
- 🔒 **Security first**: Sandboxed execution
- 📊 **Data quality**: Validation + integrity
- 📚 **Well documented**: Self-service for researchers
- 🚀 **Extensible**: Easy to add languages/features

**Next**: Proceed to Stage 2 implementation following this plan.
