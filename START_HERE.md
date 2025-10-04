# 🚀 Start Here - Quick Reference

## Instant Demo (3 Steps)

```bash
# 1. Start all services
docker-compose up -d

# 2. Wait 30 seconds for services to initialize
sleep 30

# 3. Run interactive demo
./demo.sh
```

That's it! The demo script will guide you through:
- ✅ System health checks
- ✅ Three complete examples (simple, complex, failed)
- ✅ Trace viewing and comparison
- ✅ LLM judge status
- ✅ Service logs and monitoring

---

## Manual Quick Test

```bash
# Install Python dependency
pip install httpx

# Run simple example
python examples/submit_example.py

# View the trace
python view_trace.py <trace-id-from-output>
```

---

## Project Structure

```
📁 pr-telemetry/
├── 📄 README.md              ← Complete documentation
├── 🎬 demo.sh                ← Interactive demo (START HERE!)
├── 📄 START_HERE.md          ← This file
├── 
├── 📁 examples/              ← Three E2E examples
│   ├── submit_example.py           (Simple)
│   ├── submit_complex_example.py   (Complex)
│   └── submit_failed_example.py    (Failed)
│
├── 📁 api/                   ← FastAPI backend
├── 📁 worker/                ← Celery worker (QA + Judge)
├── 📁 alembic/               ← Database migrations
├── 📁 docs/                  ← Detailed documentation
└── 🐳 docker-compose.yml     ← Service orchestration
```

---

## What Each File Does

| File | Purpose | When to Use |
|------|---------|-------------|
| `demo.sh` | Interactive menu-driven demo | **First time exploring** |
| `submit_example.py` | Simple bug fix example | Testing basic flow |
| `submit_complex_example.py` | Multi-file debugging | Advanced testing |
| `submit_failed_example.py` | Failed attempt example | Negative data testing |
| `view_trace.py` | Human-readable trace viewer | After running examples |
| `docker-compose.yml` | Start/stop all services | System control |

---

## Common Commands

```bash
# Start system
docker-compose up -d

# Stop system
docker-compose down

# View logs
docker-compose logs -f api      # API logs
docker-compose logs -f worker   # Worker logs

# Check health
curl http://localhost:8000/healthz

# Run all examples
./demo.sh  # Select option 4

# Clean restart (deletes data)
docker-compose down -v
docker-compose up -d
```

---

## Demo Script Features

The `demo.sh` script provides:

### 🎯 Examples
1. Run Simple Example
2. Run Complex Example  
3. Run Failed Example
4. Run ALL Examples

### 🔍 Monitoring
5. View System Status
6. View Service Logs
7. Compare All Examples

### ⚙️ Utilities
8. Check LLM Judge Status
9. Run Full System Test
0. Exit

---

## Expected Output

After running an example, you'll see:

```
============================================================
PR Telemetry E2E Example
============================================================

[1/5] Creating trace...
✓ Created trace: trace-abc123def456

[2/5] Uploading event chunks...
  ✓ 10 events added

[3/5] Completing trace...
✓ Trace completed

[4/5] Waiting for QA validation and judging...
✓ QA Complete!

  Judge Evaluation:
    Problem Understanding: 3.0/5
    Causal Linking: 3.0/5
    Experiment Design: 2.0/5
    Efficiency: 3.0/5
    Reproducibility: 2.5/5
    Safety & Hygiene: 5.0/5
    ⭐ Overall Score: 3.1/5
```

---

## Troubleshooting

### Problem: Services won't start
```bash
docker-compose down -v
docker-compose up -d
```

### Problem: API not responding
```bash
# Check if containers are running
docker-compose ps

# Check API logs
docker-compose logs api
```

### Problem: Examples fail with 401
```bash
# Check if AUTH_TOKEN is correct in examples/*.py
# Default is: dev_token_12345
```

---

## Next Steps

1. ✅ **Run demo script** - `./demo.sh`
2. ✅ **Explore examples** - Check `examples/` folder
3. ✅ **Read full README** - `README.md`
4. ✅ **Enable LLM Judge** - Copy `.env.example` to `.env` and add OpenAI key
5. ✅ **Review documentation** - Browse `docs/` folder

---

## Key Resources

- **Full README**: [README.md](README.md) - Complete system documentation
- **Project Plan**: [docs/STAGE1_PROJECT_PLAN.md](docs/STAGE1_PROJECT_PLAN.md) - Design decisions
- **API Docs**: http://localhost:8000/docs (when running)
- **Schema Reference**: [docs/SCHEMA.md](docs/SCHEMA.md)

---

## Quick Reference Card

| Task | Command |
|------|---------|
| **Start demo** | `./demo.sh` |
| **Start system** | `docker-compose up -d` |
| **Stop system** | `docker-compose down` |
| **Check health** | `curl http://localhost:8000/healthz` |
| **View trace** | `python view_trace.py <trace-id>` |
| **View logs** | `docker-compose logs -f` |
| **Clean reset** | `docker-compose down -v && docker-compose up -d` |

---

**Questions?** Check [README.md](README.md) for comprehensive documentation.

**Ready to start?** Run `./demo.sh` 🚀

