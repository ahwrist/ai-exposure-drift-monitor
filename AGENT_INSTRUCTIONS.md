# AEDM — Agent Coordination & Sprint Instructions

## Multi-Agent Setup (Claude Code)

Claude Code supports running multiple agents in parallel using **git worktrees**. This lets agents work on independent tasks simultaneously without stepping on each other's files.

### How to run parallel agents

**Option 1: Multiple terminal tabs (simplest)**
Open 2-3 terminal tabs, each `cd`'d into the project root. Give each agent a scoped task that doesn't overlap files with the others. Claude Code handles file locking at the process level, but you should still keep agents on separate files to avoid merge pain.

**Option 2: Git worktrees (safest for parallel work)**
```bash
# First, make an initial commit so worktrees have a base
cd ~/Documents/Projects/ai-exposure-drift-monitor
git add -A && git commit -m "Initial build: all 6 phases complete"

# Create worktrees for parallel agents
git worktree add ../aedm-agent-1 -b agent/quality-pass
git worktree add ../aedm-agent-2 -b agent/integration-tests
git worktree add ../aedm-agent-3 -b agent/notebook-and-polish

# Run claude in each worktree directory
cd ../aedm-agent-1 && claude "Read CLAUDE.md. <task here>"
cd ../aedm-agent-2 && claude "Read CLAUDE.md. <task here>"
cd ../aedm-agent-3 && claude "Read CLAUDE.md. <task here>"

# When done, merge branches back
cd ~/Documents/Projects/ai-exposure-drift-monitor
git merge agent/quality-pass
git merge agent/integration-tests
git merge agent/notebook-and-polish

# Clean up
git worktree remove ../aedm-agent-1
git worktree remove ../aedm-agent-2
git worktree remove ../aedm-agent-3
```

**Option 3: Claude Code's built-in subagents**
If you're using Claude Code with `--agent` flag or Task tool, it can spawn subagents automatically. But for this project, manual terminal tabs give you more control.

### Key rule: non-overlapping file ownership
Each agent must own distinct files. The task assignments below are designed so agents never edit the same file simultaneously.

---

## Current State Assessment

### What's Done (All 6 Phases Complete)
- All 22 source files exist and are functional
- 62/62 tests passing (core analysis coverage 93-100%)
- CLI works: `aedm analyze`, `aedm drift`, `aedm report`, `aedm dashboard`
- Sample data, reference data, docs, CI workflow all present

### What Needs Fixing (Sprint: Polish & Ship)

| # | Gap | Severity | Files Involved |
|---|-----|----------|----------------|
| 1 | **No git commits** — entire repo is untracked | CRITICAL | `.git/` |
| 2 | **No `notebooks/walkthrough.ipynb`** — spec requires it | HIGH | `notebooks/` |
| 3 | **Test coverage below 80% target** — CLI/dashboard/output untested | HIGH | `tests/` |
| 4 | **`markdown` package missing from deps** — HTML report falls back to `<pre>` | MEDIUM | `pyproject.toml`, `report.py` |
| 5 | **Lint/type errors unknown** — ruff and mypy never run | MEDIUM | all `src/` |
| 6 | **No integration test** — end-to-end CLI pipeline untested | MEDIUM | `tests/` |
| 7 | **README lacks terminal screenshot/GIF** — spec calls for it | LOW | `README.md` |
| 8 | **GitHub repo not created** — no remote, no CI running | LOW | `.git/` |

---

## Sprint Plan: 3 Parallel Agents

### AGENT 1 — "Foundation & Quality" (do this FIRST, or solo if sequential)

**Owns:** `pyproject.toml`, `src/aedm/output/report.py`, all linting/typing, git setup

**Prompt to give this agent:**
```
Read CLAUDE.md and AGENT_LOG.md. The initial build is complete (all 6 phases). Your job is the quality pass:

1. FIRST: Add "markdown" to the dependencies list in pyproject.toml (it's referenced in report.py but missing from deps).

2. Run `pip install -e ".[dev]"` to install the project in dev mode.

3. Run `ruff check src/ tests/` and fix ALL lint errors. Do NOT disable rules — fix the actual code. Common issues will be missing type annotations (ANN) and import ordering (I).

4. Run `ruff format src/ tests/` to auto-format everything.

5. Run `mypy src/aedm/` and fix type errors. Start with --ignore-missing-imports if third-party stubs are missing, but fix all internal type issues. Add `py.typed` marker file to `src/aedm/`.

6. Run `pytest --cov=aedm --cov-report=term-missing` and confirm all 62 tests still pass.

7. After all fixes, run the full check suite: `make check` (lint + typecheck + test).

8. Update AGENT_LOG.md with a "Phase 7: Quality Pass" section documenting what you fixed.

Do NOT modify test logic or analysis algorithms. Only fix lint, type, formatting, and the missing dependency. Keep all existing behavior intact.
```

### AGENT 2 — "Integration Tests & Coverage"

**Owns:** `tests/test_cli.py` (new), `tests/test_output.py` (new), `tests/test_integration.py` (new), `tests/conftest.py` (additions only)

**Prompt to give this agent:**
```
Read CLAUDE.md, AGENT_LOG.md, and PROJECT_SPEC.md. The initial build is complete with 62/62 tests passing but coverage is below the 80% target — CLI, dashboard, and output modules are untested. Your job is to add integration and output tests.

1. First run `pip install -e ".[dev]"` and confirm `pytest` passes.

2. Create `tests/test_output.py`:
   - Test `charts.py`: verify chart functions return valid Plotly Figure objects (don't test rendering, just object structure)
   - Test `report.py`: verify markdown and HTML report generation produces non-empty strings with expected sections
   - Test `export.py`: verify CSV and JSON export produce valid data with expected columns
   - Use fixtures from conftest.py for sample data

3. Create `tests/test_cli.py`:
   - Use `typer.testing.CliRunner` to test CLI commands
   - Test `aedm --version` returns version string
   - Test `aedm analyze --input data/sample/acme_corp_roles.csv --output /tmp/aedm_test/` produces output files
   - Test `aedm drift --input data/sample/acme_corp_quarterly/ --output /tmp/aedm_test_drift/` runs without error
   - Test invalid input path produces human-readable error (not raw traceback)
   - Clean up temp directories in fixtures

4. Create `tests/test_integration.py`:
   - End-to-end test: load sample CSV → compute exposure → compute drift → compute demographics → compute urgency → generate report → export
   - Verify the full pipeline produces consistent, non-empty results
   - Verify exported JSON is valid and contains all expected top-level keys

5. Add any new fixtures needed to `conftest.py` (append only, don't modify existing fixtures).

6. Run `pytest --cov=aedm --cov-report=term-missing` and report final coverage numbers.

7. Update AGENT_LOG.md with a "Phase 7: Integration Tests" section.

Target: get overall coverage above 75%. Core analysis should stay >90%.
```

### AGENT 3 — "Notebook & Polish"

**Owns:** `notebooks/walkthrough.ipynb` (new), `README.md` (minor updates), `AGENT_LOG.md` (its own section)

**Prompt to give this agent:**
```
Read CLAUDE.md, PROJECT_SPEC.md, and the docs/ directory. The initial build is complete. Your job is to create the walkthrough notebook and polish documentation.

1. First run `pip install -e .` and `pip install jupyter` to set up the environment.

2. Create `notebooks/walkthrough.ipynb` — a narrative demo notebook that walks through AEDM's capabilities:

   Cell 1: Markdown intro — what AEDM is, link to the Anthropic paper
   Cell 2: Import and load sample data
   ```python
   from aedm.ingest import parse_roles_csv, load_reference_rates
   from aedm.analysis import compute_org_exposure, detect_drift_cusum, analyze_demographics, score_org_urgency
   from aedm.output import generate_markdown_report, build_export_dataframe

   roles = parse_roles_csv("../data/sample/acme_corp_roles.csv")
   rates = load_reference_rates("../data/reference/anthropic_exposure_rates.json")
   ```
   Cell 3: Compute exposure scores, show top 10 most exposed roles in a pandas table
   Cell 4: Markdown explanation of the exposure methodology
   Cell 5: Exposure distribution visualization using charts.py
   Cell 6: Load quarterly data, run drift detection, show results
   Cell 7: Markdown on drift methodology
   Cell 8: Demographics analysis — show disparity table
   Cell 9: Urgency scoring — show priority matrix
   Cell 10: Generate and display the full report
   Cell 11: Markdown conclusion with next steps

   Make it feel like a polished data science tutorial — clear narrative, clean code, good markdown explanations between code cells. Run all cells to verify they execute without errors.

3. Review README.md — verify all links work (docs/methodology.md, docs/quickstart.md, ARCHITECTURE.md, CONTRIBUTING.md, LICENSE). Fix any broken references.

4. Review docs/quickstart.md — make sure the install and usage commands are accurate for the current codebase.

5. Update AGENT_LOG.md with a "Phase 7: Notebook & Polish" section.

The notebook is the most important deliverable — it's what visitors will click first to understand the project.
```

---

## Execution Order

**If running sequentially (one agent at a time):**
1. Agent 1 (Foundation & Quality) — must go first because lint/type fixes touch all source files
2. Agent 2 (Integration Tests) — depends on clean code from Agent 1
3. Agent 3 (Notebook & Polish) — can run anytime but benefits from stable code

**If running in parallel (recommended):**
- Start Agent 1 and Agent 3 simultaneously (no file overlap)
- Start Agent 2 after Agent 1 finishes (Agent 2 needs the lint-fixed code to write clean tests against)
- Or: start all 3 if you're comfortable resolving minor merge conflicts in `AGENT_LOG.md`

---

## After All Agents Complete

Run this yourself or give to a final agent:

```bash
# Final validation
cd ~/Documents/Projects/ai-exposure-drift-monitor
pip install -e ".[dev]"
make check  # lint + typecheck + test

# Initial commit
git add -A
git commit -m "v0.1.0: Complete AEDM build — exposure indexing, drift detection, demographic analysis, reskilling urgency scoring

6-phase build from PROJECT_SPEC.md, plus quality pass:
- Full analysis engine with CUSUM drift detection and permutation testing
- Typer CLI and Streamlit dashboard with 6 tabs
- 62+ tests, >80% coverage on core analysis
- Ruff-clean, mypy-checked, fully typed Python 3.11+
- Walkthrough notebook and comprehensive documentation

Built with Claude Code using CLAUDE.md-driven agentic development."

# Create GitHub repo and push
gh repo create ahwrist/ai-exposure-drift-monitor --public --source=. --push
```

---

## Notes for Cowork Coordination

When feeding tasks to agents from Cowork:
- Copy the exact prompt block for each agent (between the ``` markers)
- After each agent completes, have it paste its AGENT_LOG.md additions here so you can track progress
- If an agent reports errors it can't fix, bring the error back here and we'll strategize
- Each agent should take 5-15 minutes depending on the task complexity
