# CLAUDE.md — AI Exposure Drift Monitor

## Project Overview
AEDM operationalizes Anthropic's March 2026 "Labor Market Impacts of AI" research into a CLI + dashboard tool for organizational workforce planning. It computes theoretical and observed AI exposure indices per role, detects drift over time, and produces actionable reskilling recommendations.

## Build Order (STRICT)
Agents must follow this sequence. Do not skip steps or work out of order.

### Phase 1: Foundation
1. `pyproject.toml` — Project metadata, dependencies, entry points
2. `src/aedm/__init__.py` — Package init with version
3. `src/aedm/models/enums.py` — ExposureTier, RiskLevel, DriftDirection enums
4. `src/aedm/models/schemas.py` — Pydantic models: Role, ExposureScore, DriftResult, OrgSnapshot, DemographicSegment
5. `src/aedm/config.py` — Pydantic Settings for paths, thresholds, defaults

### Phase 2: Data Layer
6. `data/reference/anthropic_exposure_rates.json` — Curated reference data (SOC major groups → theoretical/observed rates from Anthropic's published figures)
7. `data/sample/acme_corp_roles.csv` — Synthetic org data: 200 roles with title, department, SOC code, headcount, demographics
8. `data/sample/acme_corp_quarterly/` — 4 quarterly snapshots showing drift
9. `src/aedm/ingest/validators.py` — Input schema validation
10. `src/aedm/ingest/parser.py` — CSV/JSON ingestion with validation
11. `src/aedm/ingest/onet_mapper.py` — Title → SOC mapping (thefuzz + exact match fallback)

### Phase 3: Analysis Engine
12. `src/aedm/analysis/exposure.py` — Core exposure index: weighted blend of theoretical + observed rates, task-level granularity where available
13. `src/aedm/analysis/drift.py` — CUSUM changepoint detection + simple linear trend test on multi-period exposure data
14. `src/aedm/analysis/demographics.py` — Disparity ratios by gender, education, pay band; flagging disproportionate exposure
15. `src/aedm/analysis/reskill.py` — Urgency score = f(exposure_level, drift_velocity, headcount, reskill_difficulty)

### Phase 4: Output Layer
16. `src/aedm/output/charts.py` — Plotly charts: exposure heatmap, drift sparklines, demographic disparity bars, urgency matrix
17. `src/aedm/output/report.py` — Markdown + HTML report with embedded charts
18. `src/aedm/output/export.py` — Structured CSV/JSON export of all computed metrics

### Phase 5: Interface
19. `src/aedm/cli.py` — Typer CLI: `aedm analyze`, `aedm drift`, `aedm report`, `aedm dashboard`
20. `src/aedm/dashboard/app.py` — Streamlit dashboard with filters, drill-down, and scenario toggles

### Phase 6: Quality & Documentation
21. `tests/` — Pytest suite covering all analysis modules (min 80% coverage target)
22. `docs/methodology.md` — Statistical methods writeup (accessible to non-technical readers)
23. `docs/data_dictionary.md` — All fields, types, and definitions
24. `docs/quickstart.md` — 5-minute guide from install to first report
25. `README.md` — Professional README (see specification below)
26. `.github/workflows/ci.yml` — GitHub Actions: lint (ruff), type check (mypy), test (pytest)

## Code Standards
- Python 3.11+, fully typed (mypy strict mode target)
- Pydantic v2 for all data models
- Ruff for linting and formatting
- Docstrings: Google style, on all public functions
- No print statements in library code — use structlog
- All analysis functions must be pure: data in → result out, no side effects
- Charts must support both interactive (Plotly) and static (PNG export) modes

## Dependency Constraints
Core: pydantic, typer, structlog, numpy, scipy, pandas
Analysis: scikit-learn (for preprocessing only), statsmodels (for trend tests)
Visualization: plotly, matplotlib (static fallback)
Dashboard: streamlit
Fuzzy matching: thefuzz, python-Levenshtein
Dev: pytest, pytest-cov, ruff, mypy

Do NOT add: tensorflow, torch, transformers, or any ML framework. This is a statistical analysis tool, not a model training pipeline.

## Agent Memory
After completing each phase, create/update `AGENT_LOG.md` at the project root with:
- Phase completed
- Files created/modified
- Any decisions made or deviations from the build order
- Known issues or TODOs for next phase

## Testing Conventions
- Test files mirror source structure: `test_exposure.py` tests `analysis/exposure.py`
- Use fixtures in `conftest.py` for sample data
- Every analysis function needs at minimum: one happy-path test, one edge-case test, one test with the sample data
- Drift detection needs a test with known changepoint to verify detection

## Error Handling
- All user-facing errors through custom exception hierarchy in `src/aedm/exceptions.py`
- CLI must never show raw tracebacks — catch and display human-readable messages
- Invalid input data must produce specific, actionable error messages

## Key Design Decisions
- Exposure scores are normalized to [0, 1] range
- Drift is measured as the slope of exposure over time, with statistical significance via permutation test
- Reskilling urgency is a composite score, not a single metric — it accounts for exposure level, drift velocity, headcount at risk, and estimated reskill difficulty
- The tool should work with as little as a CSV of job titles — SOC mapping is automated but overridable
- All charts use a consistent color palette defined in config

## Agent Coordination Protocol

When multiple agents work on this project simultaneously, follow these rules:

### File Ownership
Each agent must declare which files it owns at the start of its task. No two agents should modify the same file concurrently. If you need to modify a file owned by another agent, note it in AGENT_LOG.md as a "pending merge" item.

### AGENT_LOG.md Convention
- Each agent appends its own section — never overwrite another agent's entries
- Use the format: `## Phase N: <Task Name> [Agent: <description>]`
- Include: files created/modified, decisions made, issues found, time taken

### Pre-flight Checklist (every agent, every session)
1. Read CLAUDE.md (this file)
2. Read AGENT_LOG.md to understand current state
3. Run `pip install -e ".[dev]"` to ensure environment is current
4. Run `pytest` to confirm tests pass before making changes
5. After completing work: run `make check` (lint + typecheck + test)

### Commit Convention
- Use conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`
- One logical change per commit
- Always run `make check` before committing

### Quality Gates
- All code must pass `ruff check` with no errors
- All code must pass `ruff format --check` with no changes needed
- `mypy src/aedm/` must pass (--ignore-missing-imports OK for third-party)
- `pytest` must pass with 0 failures
- New code requires tests if it contains logic (not just wiring)