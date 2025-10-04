# 🚀 Get Started with PR Telemetry

**Welcome!** This guide will get you up and running in under 5 minutes.

## What You'll Do

1. ✅ Start the system (1 minute)
2. ✅ Run an example bug fix (2 minutes)
3. ✅ See AI evaluation results (2 minutes)

## Step 1: Start the System

```bash
# Navigate to project
cd /Users/yuqingjian/code/pr-telemetry

# Start all services (API, Worker, Database, Storage, Queue)
docker-compose up -d

# Wait ~30 seconds, then check health
curl http://localhost:8000/healthz
```

✅ **You should see:** `{"status": "healthy", ...}`

## Step 2: Run the Example

```bash
# Install HTTP client (if needed)
pip install httpx

# Run the complete example
python examples/submit_example.py
```

**What happens:**
- Creates a trace for fixing a buggy calculator
- Uploads 10 events (file edits, test runs, reasoning notes)
- Runs tests in an isolated Docker container
- AI judge evaluates the approach
- Shows scores and feedback

## Step 3: View Results

The example script will show:

```
✓ QA Complete!

Validation Results:
  Tests Passed: True
  Passed: 5, Failed: 0

Judge Evaluation:
  Problem Understanding: 3.5/5
  Causal Linking: 3.0/5
  Overall Score: 3.5/5
  
  Feedback: The developer demonstrated a systematic 
  approach to debugging...
```

## What Just Happened?

1. **Trace Created**: System recorded a complete bug-fixing session
2. **Events Captured**: 10 developer actions (edits, commands, reasoning)
3. **Tests Validated**: Ran tests in secure Docker container
4. **AI Evaluated**: Multi-dimensional scoring of debugging approach

## Next Steps

### Explore the API

```bash
# Visit interactive API docs
open http://localhost:8000/docs
```

### View Your Data

```bash
# MinIO console (object storage)
open http://localhost:9001
# Login: minioadmin / minioadmin

# Check database
docker-compose exec postgres psql -U telemetry -d pr_telemetry
```

### Create Your Own Trace

```bash
# See API examples in README.md
# Or check examples/submit_example.py for Python code
```

### View Logs

```bash
# All logs
docker-compose logs -f

# Just API
docker-compose logs -f api

# Just worker (AI evaluation)
docker-compose logs -f worker
```

## Understanding the System

### Architecture

```
Developer → API → Database (metadata)
                → Storage (artifacts)
                → Queue → Worker → Docker (tests)
                                 → AI Judge (evaluation)
```

### Key Components

- **API**: Receives events from developers
- **Database**: Stores trace metadata
- **Storage**: Saves code snapshots, test outputs
- **Worker**: Runs tests and AI evaluation
- **Judge**: Scores debugging approach (6 dimensions)

### What Gets Captured

- ✅ File edits (with diffs)
- ✅ Commands executed
- ✅ Test runs
- ✅ Git commits
- ✅ Developer reasoning (plans, hypotheses, decisions)

## Example Files

Check these out to understand the system:

```
examples/
├── repo-buggy/          # Buggy calculator (multiply function)
├── sample-trace-chunks/ # 10 events showing bug fix process
└── submit_example.py    # Script that submits the trace
```

## Stopping the System

```bash
# Stop (keeps data)
docker-compose stop

# Stop and remove data
docker-compose down -v
```

## Need Help?

**Check these resources:**
- 📖 [README.md](README.md) - Complete documentation
- 🚀 [QUICKSTART.md](QUICKSTART.md) - Detailed setup
- 📋 [SCHEMA.md](SCHEMA.md) - Data format reference
- 🧪 [TESTING.md](TESTING.md) - Verification guide

**Common issues:**
- Services won't start → Wait 60 seconds
- Port conflicts → Check ports 5432, 6379, 8000, 9000, 9001
- Example fails → Check `docker-compose logs api`

**Commands:**
```bash
make start    # Start system
make example  # Run example
make logs     # View logs
make stop     # Stop system
make clean    # Remove everything
```

## What Makes This Special?

✨ **Complete Coverage**: Captures everything from first observation to verified fix

✨ **AI-Powered Analysis**: Multi-dimensional evaluation of problem-solving approach

✨ **Research Ready**: Data format designed for training AI models

✨ **Production Grade**: Secure containers, integrity verification, scalable design

✨ **Easy to Use**: One command to start, runs everywhere via Docker

## Use Cases

1. **AI Training**: Collect high-quality bug-fixing traces for model training
2. **Research**: Study developer problem-solving strategies
3. **Education**: Analyze and improve debugging skills
4. **Benchmarking**: Create standardized datasets for code AI evaluation

---

**🎉 You're all set!**

The system is running and ready to capture bug-fixing sessions.

For integration with your IDE or custom workflow, see the [API documentation](http://localhost:8000/docs).

