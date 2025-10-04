"""LLM judge prompts and rubric."""

RUBRIC_VERSION = "1.0"

JUDGE_PROMPT_TEMPLATE = """You are an expert code reviewer evaluating a developer's bug-fixing process.

## Task
The developer was asked to fix: "{task_title}"

{task_description}

## Known Failing Tests
{failing_tests}

## Developer Actions Summary
The developer performed {num_events} actions over {duration_s:.1f} seconds:
- {num_edits} file edits across {files_touched} files
- {num_cmds} commands executed
- {num_test_runs} test runs

## Key Events

### File Edits
{file_edits}

### Test Runs
{test_runs}

### Rationale Notes
{rationales}

## Final Validation
{validation_result}

---

## Evaluation Task

Rate the developer's problem-solving approach on the following dimensions (0-5 scale):

1. **Problem Understanding (20%)**: Did they demonstrate clear understanding of the failure modes and requirements?

2. **Causal Linking (25%)**: Did they effectively connect observations to hypotheses to code changes?

3. **Experiment Design (20%)**: Was their testing strategy sound—isolating issues, incremental validation?

4. **Efficiency (15%)**: Did they minimize unnecessary edits and command usage? Was the edit locality appropriate?

5. **Reproducibility (10%)**: Are the actions clearly replayable from this trace?

6. **Safety & Hygiene (10%)**: Did they avoid dangerous commands and handle sensitive data properly?

Respond in JSON format:
{{
  "problem_understanding": <score 0-5>,
  "causal_linking": <score 0-5>,
  "experiment_design": <score 0-5>,
  "efficiency": <score 0-5>,
  "reproducibility": <score 0-5>,
  "safety_hygiene": <score 0-5>,
  "overall": <weighted average>,
  "feedback_summary": "<3-5 sentence summary of strengths and areas for improvement>"
}}
"""


def build_judge_prompt(trace_data: dict) -> str:
    """
    Build the judge prompt from trace data.
    
    Args:
        trace_data: Parsed trace document
    
    Returns:
        Formatted prompt string
    """
    # Extract summary info
    task = trace_data.get("task", {})
    task_title = task.get("title", "Unknown task")
    task_description = task.get("description", "")
    failing_tests = task.get("known_failing_tests", [])
    
    metrics = trace_data.get("metrics", {})
    events = trace_data.get("events", [])
    
    # Format failing tests
    if failing_tests:
        failing_tests_str = "\n".join(f"- {test}" for test in failing_tests)
    else:
        failing_tests_str = "Not specified"
    
    # Summarize file edits
    file_edits = [e for e in events if e.get("type") == "file_edit"]
    if file_edits:
        file_edits_str = "\n".join(
            f"- {e.get('file_path', 'unknown')}: {len(e.get('diff_unified', ''))} chars changed"
            for e in file_edits[:10]  # Limit to first 10
        )
        if len(file_edits) > 10:
            file_edits_str += f"\n... and {len(file_edits) - 10} more edits"
    else:
        file_edits_str = "No file edits"
    
    # Summarize test runs
    test_runs = [e for e in events if e.get("type") == "test_run"]
    if test_runs:
        test_runs_str = "\n".join(
            f"- {e.get('framework', 'unknown')}: {e.get('num_passed', 0)} passed, "
            f"{e.get('num_failed', 0)} failed"
            for e in test_runs
        )
    else:
        test_runs_str = "No test runs recorded"
    
    # Summarize rationales
    rationales = [e for e in events if e.get("type") == "rationale_note"]
    if rationales:
        rationales_str = ""
        for i, r in enumerate(rationales[:5]):  # First 5
            structured = r.get("structured", {})
            if structured:
                parts = []
                if structured.get("hypothesis"):
                    parts.append(f"Hypothesis: {structured['hypothesis']}")
                if structured.get("decision"):
                    parts.append(f"Decision: {structured['decision']}")
                if parts:
                    rationales_str += f"\n{i+1}. {' | '.join(parts)}"
    else:
        rationales_str = "No rationale notes provided"
    
    # Validation result
    qa = trace_data.get("qa") or {}
    validation = qa.get("validation") or {} if qa else {}
    if validation:
        tests_passed = validation.get("tests_passed", False)
        validation_result = f"Tests {'PASSED' if tests_passed else 'FAILED'}"
        if not tests_passed:
            validation_result += f" ({validation.get('num_failed', 0)} failures)"
    else:
        validation_result = "No validation performed"
    
    # Fill template
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        task_title=task_title,
        task_description=f"Description: {task_description}" if task_description else "",
        failing_tests=failing_tests_str,
        num_events=metrics.get("num_events", 0),
        duration_s=metrics.get("duration_s", 0),
        num_edits=metrics.get("num_edits", 0),
        files_touched=metrics.get("files_touched", 0),
        num_cmds=metrics.get("num_cmds", 0),
        num_test_runs=metrics.get("num_test_runs", 0),
        file_edits=file_edits_str,
        test_runs=test_runs_str,
        rationales=rationales_str,
        validation_result=validation_result
    )
    
    return prompt

