# AI Exposure Drift Monitor (AEDM)

**Measurement-first AI workforce intelligence. From research paper to operational tool.**

[![CI](https://github.com/ahwrist/ai-exposure-drift-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/ahwrist/ai-exposure-drift-monitor/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Operationalizes Anthropic's AI labor market exposure framework into a workforce planning tool.

---

## The Problem

Anthropic's March 2026 research paper, "Labor Market Impacts of AI: A New Measure and Early Evidence" (Massenkoff & McCrory), revealed a striking finding: **theoretical AI exposure far exceeds observed adoption across every occupation group.** Computer and Mathematical occupations show 94% theoretical exposure but only 33% observed exposure. This gap — the "uncovered area" — represents tasks AI *could* automate but hasn't yet.

The implications are enormous. The Brookings Institution describes AI labor market research as being in its "first inning," yet the World Economic Forum's 2025 Future of Jobs Report found that 63% of employers already cite skills gaps as the top barrier to transformation. Meanwhile, SHRM reports that 92% of CHROs expect further AI integration into their workforce — but lack the measurement tools to plan for it.

Research tells us AI is reshaping the workforce. But no organization has operational tooling to measure their specific exposure, track how it's changing, or prioritize where to invest in reskilling. AEDM bridges that gap.

## The Solution

AEDM takes the theoretical + observed exposure framework from Anthropic's research and operationalizes it for your specific organization. Point it at a CSV of your job roles and get back:

- **Exposure scores** per role, department, and org-wide
- **Drift detection** showing where exposure is accelerating
- **Demographic disparity analysis** identifying disproportionate impact
- **Reskilling urgency rankings** to prioritize investment

```bash
# Analyze your workforce
$ aedm analyze --input roles.csv --output report/

# Launch interactive dashboard
$ aedm dashboard --input roles.csv
```

## Quick Start

```bash
# Install
pip install aedm

# Run analysis on your org data
aedm analyze --input your_roles.csv --output report/

# Or use the sample data to explore
aedm analyze --input data/sample/acme_corp_roles.csv --output report/

# Launch the interactive dashboard
aedm dashboard --input your_roles.csv
```

See [docs/quickstart.md](docs/quickstart.md) for a full 5-minute walkthrough.

## Features

- **Exposure indexing** — Blended theoretical + observed AI exposure scores by role, department, and org-wide
- **Temporal drift detection** — CUSUM changepoint detection with permutation-based significance testing
- **Demographic disparity analysis** — Exposure breakdown by gender, education, and pay band with disparity flagging
- **Reskilling urgency scoring** — Composite score accounting for exposure, drift velocity, headcount, and reskill difficulty
- **Interactive dashboard** — Streamlit app with filters, drill-down, and scenario modeling
- **Report generation** — Markdown and HTML reports with embedded Plotly charts
- **Structured export** — CSV/JSON export of all computed metrics

## Methodology

AEDM's analysis pipeline is built on peer-reviewed methods adapted from Anthropic's exposure framework:

- **Exposure Index:** Weighted composite of theoretical exposure (from O\*NET task inventories) and observed exposure (calibrated against Anthropic's published rates). Observed exposure is weighted more heavily (60/40) because it reflects actual adoption, not just feasibility.
- **Drift Detection:** CUSUM (cumulative sum control chart) changepoint detection identifies when exposure trends shift. Significance is assessed via permutation testing.
- **Disparity Analysis:** Exposure-weighted headcount by demographic segment, with disparity ratios flagged when a segment exceeds 1.2x the org-wide mean.
- **Urgency Scoring:** Composite of exposure level (30%), drift velocity (25%), headcount at risk (25%), and reskill difficulty (20%).

For full statistical details, see [docs/methodology.md](docs/methodology.md).

## Data Requirements

**Minimum input:** A CSV with a `title` column containing job titles.

**Full schema for richer analysis:**

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `role_id` | string | No | Unique role identifier |
| `title` | string | **Yes** | Job title |
| `soc_code` | string | No | O\*NET SOC code (auto-mapped if absent) |
| `department` | string | No | Department name |
| `headcount` | integer | No | Number of people in role (default: 1) |
| `gender_pct_female` | float | No | Proportion female (0-1) |
| `median_salary` | integer | No | Median salary |
| `education_mode` | string | No | Most common education level |
| `remote_pct` | float | No | Proportion remote-eligible (0-1) |

## Architecture

AEDM follows a layered pipeline architecture: ingestion, analysis, and output.

```
Org Data (CSV/JSON) → Validation → SOC Mapping → Exposure Engine
                                                       ↓
                              Dashboard ← Report ← Drift/Demographics/Urgency
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

## Research Context

This tool is positioned within a growing body of AI labor market research:

- **Massenkoff & McCrory (2026)** — "Labor Market Impacts of AI: A New Measure and Early Evidence." Anthropic. Introduces the theoretical vs. observed exposure framework and the Anthropic Economic Index.
- **Brynjolfsson, Chandar & Chen (2025)** — Combined AI task-level exposure measures with ADP employment data to estimate labor market effects.
- **Acemoglu et al. (2022)** — "AI and Jobs: Evidence from Online Vacancies." Analyzed the relationship between AI exposure and job posting trends.
- **World Economic Forum (2025)** — Future of Jobs Report. Found 63% of employers cite skills gaps as the primary barrier to AI-driven transformation.

AEDM operationalizes these research findings so organizations can move from "AI will reshape the workforce" to "here is exactly where, how fast, and what to do about it."

## Development Philosophy

This project was built using **CLAUDE.md-driven agentic development** with Claude Code:

- **Strict build-order convention** — A phased build sequence in CLAUDE.md ensures reproducible agent execution from a single prompt
- **Agent memory pattern** — AGENT_LOG.md tracks decisions across sessions for continuity
- **Statistical rigor over ML complexity** — CUSUM, permutation tests, and composite scoring rather than black-box models
- **Measurement-first design** — Every output is designed to be presented to a CHRO, not just a data scientist

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style expectations, and PR process.

## License

MIT License. See [LICENSE](LICENSE) for details.
