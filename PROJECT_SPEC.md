# AI Exposure Drift Monitor — Claude Project Instructions

## Project Identity

**Project Name:** `aedm` — AI Exposure Drift Monitor
**Tagline:** "Measurement-first AI workforce intelligence. From research paper to operational tool."
**Author:** Andrew (GitHub: [your-handle])
**License:** MIT

---

## Mission Brief

You are scaffolding and building a professional, open-source CLI + dashboard tool called **AI Exposure Drift Monitor (AEDM)**. This tool operationalizes Anthropic's March 2026 "Labor Market Impacts of AI" research paper into a practical workforce planning instrument that any organization can deploy against their own job architecture.

The tool answers the question every CHRO is asking: **"How exposed is my workforce to AI automation, where is that exposure accelerating, and what should I do about it?"**

This is not a toy demo. This is a portfolio-grade project built to demonstrate:

1. Deep understanding of frontier AI labor market research (Anthropic's observed vs. theoretical exposure framework)
2. Applied causal inference and statistical rigor (changepoint detection, demographic disparity analysis)
3. Production-quality software engineering (typed Python, tested, documented, CI-ready)
4. Effective agentic development with Claude Code (CLAUDE.md-driven, single-prompt kickoff, agent memory patterns)

The end product should look like it was built by a senior data scientist at a frontier AI company, not a weekend hackathon participant — even though it was built in a weekend.

---

## Context: The Research This Builds On

Anthropic published "Labor Market Impacts of AI: A New Measure and Early Evidence" (Massenkoff & McCrory, March 2026). Key concepts to internalize:

- **Theoretical exposure:** The fraction of an occupation's tasks that LLMs could feasibly perform, derived from O*NET task-level analysis.
- **Observed exposure:** The fraction of tasks actually being automated in practice, measured via real Claude usage data (the Anthropic Economic Index).
- **The gap:** Theoretical exposure far exceeds observed exposure in every occupation group. Computer/Math occupations show 94% theoretical but only 33% observed. This gap represents the "uncovered area" — tasks AI could do but isn't yet doing.
- **Demographic skew:** The most AI-exposed workers tend to be female, more educated, and higher-paid. This is a knowledge-worker-first disruption.
- **Causal inference challenge:** The paper explicitly frames the difficulty of isolating AI's effect from confounders like interest rate cycles, trade policy, and business cycles. They use a difference-in-differences-style framework comparing more vs. less exposed occupations.

AEDM takes this framework and makes it operational for a specific organization's workforce.

---

## Architecture Overview

```
aedm/
├── CLAUDE.md                    # Agent operating instructions
├── README.md                    # Professional project README
├── ARCHITECTURE.md              # System design document
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE                      # MIT License
├── pyproject.toml               # Project config (uv/pip)
├── Makefile                     # Common commands
├── .github/
│   └── workflows/
│       └── ci.yml               # Lint + test pipeline
├── data/
│   ├── onet/                    # O*NET task mappings (gitignored raw, committed processed)
│   ├── sample/                  # Sample org data for demos
│   │   ├── acme_corp_roles.csv
│   │   └── acme_corp_quarterly/ # Multi-period snapshots for drift demo
│   └── reference/
│       └── anthropic_exposure_rates.json  # Published theoretical/observed rates by SOC
├── src/
│   └── aedm/
│       ├── __init__.py
│       ├── cli.py               # Typer-based CLI entrypoint
│       ├── config.py            # Pydantic settings
│       ├── ingest/
│       │   ├── __init__.py
│       │   ├── parser.py        # CSV/JSON org data ingestion
│       │   ├── onet_mapper.py   # Role → SOC code mapping (fuzzy + exact)
│       │   └── validators.py    # Input data validation
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── exposure.py      # Exposure index computation engine
│       │   ├── drift.py         # Changepoint / trend detection (CUSUM, Bayesian)
│       │   ├── demographics.py  # Disparity analysis by segment
│       │   └── reskill.py       # Reskilling urgency scoring
│       ├── models/
│       │   ├── __init__.py
│       │   ├── schemas.py       # Pydantic data models
│       │   └── enums.py         # Exposure tiers, risk levels
│       ├── output/
│       │   ├── __init__.py
│       │   ├── report.py        # Markdown/HTML report generator
│       │   ├── charts.py        # Plotly/matplotlib visualization engine
│       │   └── export.py        # CSV/JSON export
│       └── dashboard/
│           ├── __init__.py
│           └── app.py           # Streamlit interactive dashboard
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_ingest.py
│   ├── test_exposure.py
│   ├── test_drift.py
│   ├── test_demographics.py
│   └── test_reskill.py
├── notebooks/
│   └── walkthrough.ipynb        # Narrative demo notebook
└── docs/
    ├── methodology.md           # Statistical methodology writeup
    ├── data_dictionary.md       # Field definitions
    └── quickstart.md            # 5-minute getting started guide
```

---

## CLAUDE.md Specification

The CLAUDE.md file is the most critical file in this repo. It governs how Claude Code (or any agentic coding assistant) operates within this project. Write it with the following structure and content:

```markdown
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
```

---

## README.md Specification

The README must be best-in-class. Structure:

### Header
- Project name + tagline
- Badges: CI status, Python version, license, code style (ruff)
- One-line description: "Operationalizes Anthropic's AI labor market exposure framework into a workforce planning tool."

### The Problem
2-3 paragraphs establishing the problem space. Reference:
- Anthropic's March 2026 paper finding that theoretical AI exposure far exceeds observed adoption
- The Brookings "first inning" framing of AI labor market research
- The WEF finding that 63% of employers cite skills gaps as the top barrier to transformation
- The SHRM finding that 92% of CHROs expect further AI integration but lack measurement tools

Frame the gap: "Research tells us AI is reshaping the workforce. But no organization has operational tooling to measure their specific exposure, track how it's changing, or prioritize where to invest in reskilling."

### The Solution
Brief description of what AEDM does, with a terminal screenshot or GIF showing:
1. Running `aedm analyze --input roles.csv`
2. The exposure heatmap output
3. The drift detection summary

### Quick Start
```bash
pip install aedm
aedm analyze --input your_roles.csv --output report/
aedm dashboard --input your_roles.csv
```

### Features
- Exposure indexing by role, department, and org-wide
- Temporal drift detection with statistical significance
- Demographic disparity analysis (gender, education, pay band)
- Reskilling urgency scoring and prioritization
- Interactive Streamlit dashboard
- Markdown and HTML report generation
- CSV/JSON structured export

### Methodology
Brief overview with link to `docs/methodology.md`. Emphasize:
- Built on Anthropic's theoretical + observed exposure framework
- CUSUM changepoint detection for drift
- Permutation-based significance testing
- Composite reskilling urgency score

### Data Requirements
Minimal input spec: what columns are required, what's optional, what format.

### Architecture
Link to ARCHITECTURE.md, brief diagram.

### Research Context
Paragraph positioning this tool within the broader AI labor market research ecosystem. Cite:
- Massenkoff & McCrory (2026) — Anthropic
- Brynjolfsson, Chandar & Chen (2025) — AI exposure + ADP employment data
- Acemoglu et al. (2022) — AI and online vacancies
- WEF Future of Jobs Report 2025

### Development Philosophy
Short section on how this project was developed:
- CLAUDE.md-driven agentic development with Claude Code
- Strict build-order convention for reproducible agent execution
- Agent memory pattern for session continuity
- Emphasis on statistical rigor over ML complexity

### Contributing
Link to CONTRIBUTING.md.

### License
MIT.

---

## ARCHITECTURE.md Specification

Write a clean system design document covering:

1. **System Context Diagram** (Mermaid): User → CLI/Dashboard → Analysis Engine → Data Layer → Output
2. **Data Flow**: Raw org data → Validation → SOC Mapping → Exposure Computation → Drift Analysis → Demographic Segmentation → Urgency Scoring → Report/Dashboard
3. **Key Components**: One paragraph per module describing responsibility and interface
4. **Data Model**: Mermaid entity diagram showing Role, ExposureScore, DriftResult, OrgSnapshot relationships
5. **Extension Points**: Where someone would plug in additional data sources, alternative exposure models, or custom scoring functions
6. **Design Rationale**: Why statistical methods over ML, why Pydantic over dataclasses, why Typer over argparse, why Plotly over other charting libs

---

## CONTRIBUTING.md Specification

Standard open-source contribution guide:
- How to set up the dev environment
- How to run tests
- Code style expectations (ruff, mypy)
- PR process
- Issue labeling conventions
- Code of conduct reference

---

## Sample Data Specification

### `acme_corp_roles.csv`
Generate 200 rows of realistic synthetic data:

| Column | Type | Description |
|--------|------|-------------|
| role_id | str | Unique identifier (e.g., "R001") |
| title | str | Job title (realistic corporate titles) |
| soc_code | str | O*NET SOC code (6-digit) |
| department | str | Department name (Engineering, Finance, HR, Legal, Marketing, Operations, Sales, IT, R&D, Executive) |
| headcount | int | Number of people in this role (1-50) |
| gender_pct_female | float | Percentage female (0-1) |
| median_salary | int | Median salary for this role |
| education_mode | str | Most common education level (High School, Associate, Bachelor, Master, Doctorate) |
| remote_pct | float | Percentage remote-eligible (0-1) |

Make the data realistic:
- Software Engineers should map to SOC 15-1252
- Financial Analysts to SOC 13-2051
- HR Specialists to SOC 13-1071
- Include a mix of high-exposure (programmers, analysts, admins) and low-exposure (facilities, field roles) positions
- Salary distributions should be realistic for role types
- Gender distributions should reflect known occupational patterns

### `acme_corp_quarterly/`
Four CSV files (`q1_2025.csv` through `q4_2025.csv`) with the same schema but showing realistic drift:
- Some roles gain headcount as the org grows
- Administrative and data entry roles shrink slightly
- New roles appear in Q3-Q4 (e.g., "AI Operations Analyst")
- Exposure rates should show observable acceleration in some departments

### `anthropic_exposure_rates.json`
Structure:
```json
{
  "metadata": {
    "source": "Massenkoff & McCrory (2026). Labor Market Impacts of AI.",
    "retrieved": "2026-03-15",
    "notes": "Rates represent SOC major group aggregates from published figures"
  },
  "rates": {
    "11-0000": {
      "group_name": "Management",
      "theoretical_exposure": 0.913,
      "observed_exposure": 0.18,
      "coverage_gap": 0.733
    },
    "13-0000": {
      "group_name": "Business and Financial Operations",
      "theoretical_exposure": 0.943,
      "observed_exposure": 0.20,
      "coverage_gap": 0.743
    }
  }
}
```

Include all 22 SOC major groups from Anthropic's published data.

---

## Methodology Document Specification (`docs/methodology.md`)

Write this for a dual audience: a data-literate CHRO and a fellow data scientist. Sections:

1. **Exposure Index Construction**
   - How theoretical exposure is derived from O*NET task inventories
   - How observed exposure is calibrated against Anthropic's published rates
   - The weighted composite formula and its rationale
   - Limitations and assumptions

2. **Drift Detection**
   - Why CUSUM (cumulative sum control chart) for changepoint detection
   - The null hypothesis and test statistic
   - How significance is assessed via permutation testing
   - Minimum data requirements (at least 3 time periods recommended, 4+ for reliable detection)
   - Alternative: simple linear trend with confidence interval

3. **Demographic Disparity Analysis**
   - Exposure-weighted headcount by segment
   - Disparity ratio: segment exposure vs. org-wide mean
   - Statistical significance of disparities
   - Connection to Anthropic's finding that exposure skews female/educated/higher-paid

4. **Reskilling Urgency Score**
   - Component weights: exposure level (0.3), drift velocity (0.25), headcount at risk (0.25), reskill difficulty proxy (0.2)
   - How reskill difficulty is estimated (distance between current SOC and nearest lower-exposure SOC in skill space)
   - Score normalization and tier assignment (Critical / High / Moderate / Low)

5. **Limitations**
   - Honest limitations section: SOC-level granularity may miss within-occupation variation, observed exposure rates are calibrated to Anthropic's platform data and may not generalize perfectly, drift detection requires longitudinal data that many orgs don't yet have

---

## Key Technical Implementation Notes

### Exposure Computation (`analysis/exposure.py`)
```python
def compute_exposure_index(
    role: Role,
    reference_rates: dict[str, ExposureRate],
    weight_theoretical: float = 0.4,
    weight_observed: float = 0.6,
) -> ExposureScore:
    """
    Compute blended exposure index for a single role.
    
    Weights observed exposure more heavily because it reflects
    actual adoption patterns, not just theoretical feasibility.
    """
```

### Drift Detection (`analysis/drift.py`)
```python
def detect_drift_cusum(
    exposure_series: list[float],
    threshold: float = 1.5,
    min_periods: int = 3,
) -> DriftResult:
    """
    CUSUM changepoint detection on exposure time series.
    
    Returns drift direction, magnitude, changepoint index,
    and p-value from permutation test.
    """
```

### Reskilling Urgency (`analysis/reskill.py`)
```python
def score_reskill_urgency(
    exposure: ExposureScore,
    drift: DriftResult | None,
    headcount: int,
    reskill_difficulty: float,
    weights: UrgencyWeights | None = None,
) -> UrgencyScore:
    """
    Composite urgency score combining exposure, drift, scale, and difficulty.
    
    Returns normalized score [0,1] and tier assignment.
    """
```

---

## Dashboard Specification (`dashboard/app.py`)

The Streamlit dashboard should include:

1. **Org Overview Tab**
   - Total headcount, mean exposure, highest-risk departments
   - Exposure distribution histogram
   - Top 10 most exposed roles table

2. **Exposure Heatmap Tab**
   - Department × exposure tier heatmap
   - Drill-down to individual roles on click
   - Toggle between theoretical, observed, and blended exposure

3. **Drift Analysis Tab** (only if multi-period data provided)
   - Sparkline grid showing exposure trend per department
   - Highlighted changepoints
   - Statistical summary table

4. **Demographics Tab**
   - Disparity bar chart by gender, education, pay band
   - Exposure-weighted headcount by segment
   - Disparity flags for segments >1.2x org mean

5. **Reskilling Priority Tab**
   - Urgency matrix (exposure × drift velocity, sized by headcount)
   - Ranked priority list with tier badges
   - Estimated reskilling investment (headcount × difficulty proxy)

6. **Scenario Tab**
   - Slider: "What if observed exposure catches up to X% of theoretical?"
   - Shows projected headcount impact and urgency shift
   - Simple Monte Carlo confidence bands

---

## What Success Looks Like

When someone visits this GitHub repo, they should immediately see:

1. **A professional README** that frames the problem, cites the research, and shows the tool in action
2. **Clean, typed, tested code** that a senior engineer would respect
3. **A CLAUDE.md** that demonstrates mastery of agentic development patterns
4. **A methodology doc** that demonstrates statistical rigor without being inaccessible
5. **Sample data and a working demo** that lets anyone try it in 5 minutes
6. **A development philosophy section** that explicitly highlights Claude Code as the development tool — showing sophisticated AI-augmented development practices

The overall impression should be: "This person understands the frontier AI workforce research deeply, can translate it into operational tooling, writes production-quality code, and develops effectively with AI agents. They belong at Anthropic/OpenAI/Google."

---

## Agent Kickoff Command

Once the repo structure and all markdown files are scaffolded, the build can be kicked off with:

```bash
claude "Read CLAUDE.md. Execute the build order starting at Phase 1. After each phase, update AGENT_LOG.md and proceed to the next phase. Do not skip phases. If you encounter an ambiguity, make a reasonable decision, document it in AGENT_LOG.md, and continue."
```

---

## Final Notes

- Every file should feel intentional. No boilerplate for boilerplate's sake.
- The sample data should tell a story — Acme Corp is a mid-size tech company going through AI adoption, and the data should show that narrative.
- The charts should use a cohesive, professional color palette. Suggested: deep navy (#1B2A4A), teal (#2EC4B6), warm amber (#FF6B35), soft gray (#E8E8E8), alert red (#E63946).
- Error messages should be helpful and specific, not generic.
- The CLI output should be clean and scannable — use rich or similar for terminal formatting.
- This is a tool that could realistically be presented to a CHRO. Design every output with that audience in mind.
