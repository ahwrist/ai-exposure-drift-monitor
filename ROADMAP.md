# AEDM Roadmap: Ship-Ready for Anthropic People Research Scientist

**Evaluation date:** 2026-04-10
**Target:** Stand-out portfolio artifact for Anthropic People Research Scientist interview

---

## Current State Assessment

### What's Built (Solid)

The core pipeline is functional end-to-end: CSV ingestion → SOC mapping → exposure scoring → drift detection → demographics → urgency ranking → reports + dashboard. 98 tests pass at 82% coverage. The methodology doc is well-written. The reference rates JSON has all 22 SOC major groups with real figures from the Anthropic paper. Git has 4 clean commits. CI runs lint, typecheck, and tests across Python 3.11-3.13.

### What's Missing (Critical Gaps)

**1. The Streamlit dashboard doesn't communicate YOUR methodology story.**
Right now the dashboard is a data viewer. It shows scores and charts but never explains *why* these numbers matter, *how* they're computed, or *what connection they have to Anthropic's research*. An interviewer opening this app sees a Plotly histogram and a table — not the intellectual framework that makes this project interesting. The dashboard is the first thing someone will click. It needs to teach, not just display.

**2. The "Methodology" tab is missing from the dashboard.**
The docs/methodology.md is excellent, but it's a markdown file sitting in a docs folder. None of that content appears in the app itself. The Anthropic paper's core insight — the theoretical vs. observed gap — needs to be visually prominent in the tool, not buried in documentation.

**3. The Drift tab is a dead end.**
Tab 3 just says "Drift analysis requires multi-period data" with a blue info box. For a portfolio piece, this tab should load the included quarterly sample data and show a working drift analysis with CUSUM visualization, not punt to the CLI.

**4. No "Research → Tool" narrative in the app.**
The README does this well. The dashboard does not. There's no callout that says "Anthropic's research found X → AEDM operationalizes it as Y." This is the single most important thing for the interview: showing you can take research and make it actionable.

**5. No GitHub push yet.**
The repo exists locally with 4 commits but hasn't been pushed. The CI badge in the README points to a repo that doesn't exist yet.

**6. No live demo / deployment story.**
No Streamlit Cloud config, no Dockerfile, no deploy instructions. For a portfolio piece, having a clickable live link dramatically increases impact.

### What's Good But Could Be Better

- **Scenario tab** is a strong concept (closing the theoretical-observed gap) but needs narrative framing
- **Demographic disparity analysis** directly maps to the role's focus on studying "workforce dynamics" and "ensuring responsible research practices" — deserves more prominence
- **The reference rates JSON** is well-structured but the provenance story (how you extracted it from the paper) isn't told anywhere in the app
- **The notebook** exists but won't be the first thing an interviewer sees

---

## Prioritized Roadmap

### P0 — Ship Blockers (Do First)

#### Task 1: Add Methodology Showcase to Dashboard

Add a new "Methodology" tab (or make it the second tab) that:
- Visualizes the theoretical vs. observed exposure gap as a grouped bar chart across all 22 SOC groups (this is the paper's signature finding)
- Shows the "uncovered area" — the gap between theoretical and observed — as a distinct visual element
- Includes inline annotations explaining: "Theoretical exposure measures what AI *could* do (O*NET task analysis). Observed exposure measures what AI *is* doing (Anthropic Economic Index)."
- Links the 60/40 weighting decision to the research rationale
- Has a "How This Tool Works" expandable section with the pipeline diagram

#### Task 2: Make Drift Tab Functional with Sample Data

The drift tab should auto-load the quarterly sample data (data/sample/acme_corp_quarterly/) and show:
- A working CUSUM analysis with sparkline chart per department
- The permutation test p-values
- A visual changepoint indicator
- Brief explanation of why CUSUM was chosen over PELT or Bayesian methods

#### Task 3: Add Research Context Callouts Throughout Dashboard

Every tab should have a brief (~2 sentence) callout connecting the analysis to the research. Examples:
- Org Overview: "Anthropic's research found that theoretical AI exposure far exceeds observed adoption across every occupation. Your org's mean blended exposure of X% reflects this pattern."
- Demographics: "The research found AI exposure systematically skews toward female workers, more-educated workers, and higher-paid workers. Here's how your organization compares."
- Urgency: "The gap between theoretical and observed exposure — the 'uncovered area' — signals where adoption is likely to accelerate. Roles in this quadrant face both high current exposure and high growth potential."

#### Task 4: Push to GitHub

- Verify .gitignore covers .venv, __pycache__, .coverage, .mypy_cache, .ruff_cache, .pytest_cache
- Create GitHub repo ahwrist/ai-exposure-drift-monitor
- Push all commits
- Verify CI badge goes green

### P1 — High Impact Polish

#### Task 5: Add Coverage Gap Visualization

Create a standout chart — a "coverage gap" waterfall or butterfly chart showing theoretical vs. observed vs. gap for each SOC group. This is the paper's most memorable visual finding and should be a hero element in the app.

#### Task 6: Streamlit Cloud Deployment

- Add a `streamlit_app.py` entry point at root (or configure existing)
- Add `.streamlit/config.toml` with theme settings
- Deploy to Streamlit Community Cloud
- Add "Live Demo" badge to README

#### Task 7: README Enhancement for Portfolio Context

Add a "Why This Exists" section that tells the story:
- "I read Anthropic's March 2026 labor market research and saw an opportunity to operationalize their theoretical vs. observed framework..."
- Mention the agentic development process as a meta-demonstration of working with AI
- Add a screenshot/GIF of the dashboard

#### Task 8: Strengthen the Demographic Equity Angle

The People Research Scientist role explicitly mentions "navigate research ethics considerations when studying employee data." Add:
- A note in the demographics tab about ethical considerations (correlation ≠ causation, intersectionality limitations)
- Privacy-by-design callout: the tool never stores individual employee data, only role-level aggregates
- A "Limitations & Responsible Use" section in the dashboard sidebar

### P2 — Nice to Have

#### Task 9: Interactive Weight Tuning

Let users adjust the theoretical/observed weights (currently hardcoded 40/60) and urgency component weights via sliders, with real-time score recalculation. This demonstrates the configurability of the framework.

#### Task 10: Export from Dashboard

Add download buttons for CSV/JSON/Markdown report directly from the Streamlit UI, so users don't need the CLI.

#### Task 11: Walkthrough Notebook Cleanup

Verify the notebook runs cleanly, add a Binder badge or Colab link for one-click access.

---

## Agent Handoff Tasks

Below are precise, self-contained prompts for Claude Code agents. Run them in order (P0 first), though Tasks 1-3 can be parallelized.

---

### Agent Task 1: Dashboard Methodology & Research Context

```
You are working on the AEDM project at ~/Documents/Projects/ai-exposure-drift-monitor.
Activate the venv first: source .venv/bin/activate

READ FIRST: docs/methodology.md, src/aedm/dashboard/app.py, data/reference/anthropic_exposure_rates.json, CLAUDE.md

Your job is to transform the Streamlit dashboard from a data viewer into a methodology showcase. This is a portfolio project for an Anthropic interview — the dashboard must TEACH the viewer about the research-to-tool pipeline.

CHANGES TO src/aedm/dashboard/app.py:

1. ADD a new tab "How It Works" as the SECOND tab (after Org Overview, before Heatmap). This tab should:
   a. Show a grouped bar chart of ALL 22 SOC major groups with three bars each: theoretical exposure (blue), observed exposure (teal), and the coverage gap (amber/light). Load this from the reference rates JSON. Sort by theoretical exposure descending. This is the paper's signature visual.
   b. Below the chart, add an st.expander("Methodology Details") containing:
      - Brief explanation of the exposure index formula (40/60 weighting and why)
      - Brief explanation of CUSUM drift detection and why it was chosen
      - Brief explanation of the urgency scoring composite
      - Each should be 2-3 sentences, not the full methodology doc
   c. Add a pipeline diagram using st.markdown with a simple ASCII/text flow: "Your CSV → SOC Mapping → Exposure Scoring → Drift Detection → Demographics → Urgency Rankings"

2. ADD research context callouts to existing tabs using st.caption() or st.info():
   - Org Overview tab: After the metrics row, add: "Anthropic's March 2026 research found that theoretical AI exposure far exceeds observed adoption. The 'uncovered area' between these rates signals where AI adoption is likely to accelerate. [Source: Massenkoff & McCrory, 2026]"
   - Demographics tab: Before the chart, add: "Anthropic's research found AI exposure systematically skews toward female workers, more-educated workers, and higher-paid workers — driven by the concentration of knowledge work tasks in these segments."
   - Reskilling tab: Before the matrix, add: "Urgency combines four factors: current exposure (30%), drift velocity (25%), headcount at risk (25%), and reskill difficulty (20%). Roles in the upper-right quadrant face both high exposure and high urgency."
   - Scenario tab: Before the slider, add: "The gap between theoretical and observed exposure averages 50-65 percentage points across occupations. This scenario models what happens as that gap narrows."

3. ADD a sidebar section "About AEDM" at the bottom of the sidebar:
   - "Built on Anthropic's 'Labor Market Impacts of AI' framework (Massenkoff & McCrory, March 2026)"
   - Link to the paper: https://www.anthropic.com/research/labor-market-impacts
   - "Statistical methods: CUSUM changepoint detection, permutation testing, composite scoring"

DO NOT modify any analysis modules (src/aedm/analysis/*), only the dashboard.
Run the app with: streamlit run src/aedm/dashboard/app.py -- data/sample/acme_corp_roles.csv
Verify it loads without errors.
Run: make check (ruff + mypy + pytest) and fix any issues.
```

---

### Agent Task 2: Make Drift Tab Functional

```
You are working on the AEDM project at ~/Documents/Projects/ai-exposure-drift-monitor.
Activate the venv first: source .venv/bin/activate

READ FIRST: src/aedm/dashboard/app.py, src/aedm/analysis/drift.py, src/aedm/ingest/parser.py, src/aedm/output/charts.py, data/sample/acme_corp_quarterly/

Your job is to make the Drift Analysis tab in the Streamlit dashboard functional by loading the included quarterly sample data.

CHANGES TO src/aedm/dashboard/app.py (Tab 3 — Drift Analysis):

Replace the current placeholder content with:

1. Auto-detect and load quarterly snapshots from data/sample/acme_corp_quarterly/ using load_quarterly_snapshots(). Use a try/except — if no quarterly data exists, fall back to the current info message.

2. For each quarterly snapshot, compute exposure scores and build department-level time series (same logic as the CLI drift command).

3. Run detect_org_drift() on the department series.

4. Show results:
   a. Use the drift_sparklines() chart from charts.py to show slope by department
   b. Below the chart, show a table with: Department, Direction (with color: red=Accelerating, green=Decelerating, gray=Stable), Trend Slope, p-value, Periods
   c. Add an st.expander("How Drift Detection Works") with 2-3 sentences on CUSUM + permutation testing

5. If any departments show significant drift, add an st.warning with a summary.

You may need to add imports at the top of app.py:
- from aedm.analysis.drift import detect_org_drift
- from aedm.ingest.parser import load_quarterly_snapshots
- from aedm.output.charts import drift_sparklines

Also update the load_data function or create a separate cached function for drift data.

DO NOT modify analysis modules. Only modify dashboard/app.py.
Run: streamlit run src/aedm/dashboard/app.py -- data/sample/acme_corp_roles.csv
Verify the drift tab shows real data. Run: make check
```

---

### Agent Task 3: Coverage Gap Hero Chart + Demographic Ethics

```
You are working on the AEDM project at ~/Documents/Projects/ai-exposure-drift-monitor.
Activate the venv first: source .venv/bin/activate

READ FIRST: src/aedm/output/charts.py, src/aedm/dashboard/app.py, data/reference/anthropic_exposure_rates.json

Your job is to add two things:

PART A: Coverage Gap Chart (in src/aedm/output/charts.py)

Add a new function: coverage_gap_chart(reference_rates: dict[str, ExposureRate]) -> go.Figure

This creates a horizontal grouped bar chart showing, for each SOC major group (sorted by theoretical exposure descending):
- Theoretical exposure (NAVY color)
- Observed exposure (TEAL color)
- Coverage gap (AMBER color, lighter opacity)

Use the group_name field for y-axis labels (not SOC codes).
Add a vertical annotation or line at the mean gap.
Title: "The AI Adoption Gap: Theoretical vs. Observed Exposure by Occupation"
Subtitle via annotation: "Source: Massenkoff & McCrory (2026), Anthropic Economic Index"

This should be the most visually compelling chart in the whole app.

PART B: Responsible Use Section (in src/aedm/dashboard/app.py)

In the Demographics tab, after the disparity chart and table, add an st.expander("Responsible Use & Limitations"):
- "Disparity ratios describe correlation, not causation. A high ratio means a demographic segment faces more AI-exposed roles — not that demographic characteristics cause exposure."
- "AEDM operates on role-level aggregates, not individual employee data. No PII is stored or processed."
- "Intersectional analysis (e.g., gender × education × pay band) is not currently supported. Single-dimension analysis may mask compounding effects."
- "These findings should inform planning conversations, not determine individual employment outcomes."

In the sidebar, after the "About AEDM" section (if it exists) or at the bottom, add:
st.sidebar.caption("⚖️ This tool measures exposure and correlation, not causation. See the Demographics tab for responsible use guidance.")

Run: make check and fix any lint/type issues.
```

---

### Agent Task 4: GitHub Push + Deploy Config

```
You are working on the AEDM project at ~/Documents/Projects/ai-exposure-drift-monitor.

Your job is to prepare for GitHub push and Streamlit Cloud deployment.

1. VERIFY .gitignore includes: .venv/, __pycache__/, *.pyc, .coverage, .mypy_cache/, .ruff_cache/, .pytest_cache/, *.egg-info/, dist/, build/, .env, report/

2. CREATE .streamlit/config.toml with theme settings:
   [theme]
   primaryColor = "#0A2540"
   backgroundColor = "#FFFFFF"
   secondaryBackgroundColor = "#F5F7FA"
   textColor = "#1A1A2E"
   font = "sans serif"

3. CREATE streamlit_app.py at root (entry point for Streamlit Cloud):
   """Entry point for Streamlit Cloud deployment."""
   from aedm.dashboard.app import main
   main()

4. UPDATE README.md:
   - Add a "Live Demo" badge placeholder: [![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://aedm.streamlit.app)
   - Add a "Why This Project" section after "The Solution" that briefly explains: built to operationalize Anthropic's research, demonstrates research-to-tool pipeline, built using agentic development with Claude Code
   - Add a screenshot placeholder: ![Dashboard Screenshot](docs/screenshot.png)

5. RUN the full quality gate: make check
   Fix any issues.

6. STAGE all changes and CREATE a single clean commit:
   "feat: add deployment config and README enhancements for public launch"

7. Push to GitHub:
   git remote add origin https://github.com/ahwrist/ai-exposure-drift-monitor.git  (if not already added)
   git push -u origin main

Note: If the GitHub repo doesn't exist yet, create it first:
   gh repo create ahwrist/ai-exposure-drift-monitor --public --description "Operationalizes Anthropic's AI labor market exposure framework into a workforce planning tool" --source=. --push
```

---

### Agent Task 5: Weight Tuning + Dashboard Export

```
You are working on the AEDM project at ~/Documents/Projects/ai-exposure-drift-monitor.
Activate the venv first: source .venv/bin/activate

READ FIRST: src/aedm/dashboard/app.py, src/aedm/analysis/exposure.py, src/aedm/output/export.py

Your job is to add interactive weight tuning and export capabilities to the dashboard.

PART A: Weight Tuning (Sidebar)

In the sidebar, after the department filter, add an st.expander("Advanced: Adjust Weights"):
1. Two sliders for exposure weighting:
   - "Theoretical weight" (0.0-1.0, default 0.4, step 0.05)
   - "Observed weight" (auto-computed as 1 - theoretical)
   - st.caption explaining: "Higher observed weight = more grounded in actual AI adoption. Higher theoretical weight = more forward-looking."

2. When weights change, recompute exposure scores using the custom weights (pass to compute_org_exposure). This requires modifying the load_data function or adding a separate computation path — be careful with st.cache_data.

PART B: Export Buttons

At the bottom of each main tab, add download buttons:
- Org Overview: "Download Exposure Scores (CSV)"
- Demographics: "Download Disparity Analysis (CSV)"
- Reskilling: "Download Urgency Rankings (CSV)"

Use st.download_button with appropriate pandas DataFrames converted to CSV.

Run: make check and fix any issues.
Commit: "feat: add interactive weight tuning and dashboard export"
```

---

## Execution Order

1. **Agents 1, 2, 3** — Run in parallel (all modify dashboard/app.py but different tabs/sections; may need manual merge)
2. **Agent 4** — Run after 1-3 are merged and committed
3. **Agent 5** — Run after Agent 4

**Estimated total agent time:** 45-75 minutes across all tasks

---

## How This Maps to the Role

| Role Requirement | AEDM Demonstrates |
|---|---|
| Design & analyze employee listening programs | Survey-like framework: ingest role data, score exposure, segment by demographics |
| Apply psychometric/measurement methods | Composite scoring with validated weights, CUSUM changepoint detection, permutation testing |
| Study organizational dynamics | Department-level analysis, cross-functional exposure heatmaps, temporal drift |
| Build compelling visualizations & dashboards | Streamlit app with Plotly, 6+ interactive tabs, scenario modeling |
| Present findings to senior leadership | CHRO-oriented design, executive summary reports, tier-based action recommendations |
| Navigate research ethics in employee data | Responsible use section, role-level aggregation (no PII), limitations disclosure |
| Develop evidence-based people decisions | Research paper → operational tool pipeline, actionable urgency rankings |
| Novel frameworks from behavioral research | Operationalized Anthropic's theoretical-vs-observed framework into a workforce planning tool |
