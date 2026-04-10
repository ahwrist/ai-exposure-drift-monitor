# Quick Start Guide

Get from install to your first AI exposure report in 5 minutes.

---

## 1. Install

```bash
pip install aedm
```

Or install from source:

```bash
git clone https://github.com/ahwrist/ai-exposure-drift-monitor.git
cd ai-exposure-drift-monitor
pip install -e .
```

## 2. Prepare Your Data

AEDM needs a CSV with at minimum a `title` column containing job titles:

```csv
title
Software Engineer
Financial Analyst
HR Coordinator
Marketing Manager
Data Entry Clerk
```

For richer analysis, include additional columns:

```csv
role_id,title,soc_code,department,headcount,gender_pct_female,median_salary,education_mode
R001,Software Engineer,15-1252,Engineering,45,0.28,145000,Bachelor
R002,Financial Analyst,13-2051,Finance,12,0.55,85000,Bachelor
R003,HR Coordinator,13-1071,HR,8,0.78,62000,Bachelor
```

See [data_dictionary.md](data_dictionary.md) for full field definitions.

## 3. Run Analysis

```bash
# Single-snapshot analysis
aedm analyze --input your_roles.csv --output report/
```

This will:
1. Validate your input data
2. Map job titles to SOC codes (if not provided)
3. Compute exposure scores for each role
4. Generate an exposure report in `report/`

## 4. Explore the Results

The output directory contains:

- `exposure_report.md` — Markdown report with summary statistics
- `exposure_report.html` — HTML report with interactive charts
- `exposure_scores.csv` — Role-level exposure data
- `exposure_scores.json` — Structured JSON export

## 5. Try the Dashboard

```bash
aedm dashboard --input your_roles.csv
```

This launches an interactive Streamlit dashboard where you can:
- View the org-wide exposure distribution
- Drill into department-level heatmaps
- Explore demographic disparity analysis
- See reskilling priority rankings
- Run "what if" scenarios

## 6. Drift Detection (Multi-Period)

If you have workforce data from multiple time periods:

```bash
aedm drift --input-dir quarterly_snapshots/ --output report/
```

Place each period's CSV in a directory, named in sortable order (e.g., `q1_2025.csv`, `q2_2025.csv`). AEDM will detect changepoints and trend shifts.

## Try the Sample Data

AEDM ships with synthetic data for a fictional "Acme Corp":

```bash
# Single-period analysis
aedm analyze --input data/sample/acme_corp_roles.csv --output report/

# Multi-period drift analysis
aedm drift --input-dir data/sample/acme_corp_quarterly/ --output report/

# Interactive dashboard
aedm dashboard --input data/sample/acme_corp_roles.csv
```

## Next Steps

- Read the [Methodology](methodology.md) to understand the statistical methods
- Review the [Data Dictionary](data_dictionary.md) for field definitions
- Check [ARCHITECTURE.md](../ARCHITECTURE.md) for system design details
- See [CONTRIBUTING.md](../CONTRIBUTING.md) to get involved
