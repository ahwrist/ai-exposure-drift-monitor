# Statistical Methodology

This document describes the analytical methods used by AEDM. It is written for a dual audience: data-literate workforce leaders who need to understand what the tool is telling them, and data scientists who want to evaluate the statistical rigor.

---

## Research Context and Contribution

AEDM is situated within a rapidly developing body of research on AI's labor market effects. The tool operationalizes findings from this literature into organizational measurement.

### Foundational Framework

**Massenkoff & McCrory (2026), "Labor Market Impacts of AI: A New Measure and Early Evidence."** This Anthropic research paper provides the core framework AEDM builds on. It introduces two complementary measures of AI exposure — theoretical (what LLMs *could* do) and observed (what they *are* doing) — and documents the substantial gap between them across all 22 SOC major groups. Key findings that AEDM operationalizes:

- 97% of observed Claude tasks fall into categories rated as theoretically feasible, yet actual coverage remains far below theoretical ceilings
- Top-exposure-quartile workers are 16pp more female, 11pp more white, nearly 2x more likely Asian, hold graduate degrees at 17.4% vs. 4.5%, and earn 47% more
- No systematic unemployment increase, but hiring of 22-25 year olds in exposed occupations slowed ~14% (half a percentage point per month in job-finding rate)
- BLS projections: occupations with higher exposure grow 0.6pp less per 10-point coverage increase

**Anthropic Economic Index (March 2026).** Provides the real-world usage data that grounds the "observed" half of AEDM's exposure scores. Key patterns: high-tenure users (6+ months) show 10% higher success rates and are 7pp more likely to use Claude for work; Computer and Mathematical occupations account for 35% of Claude.ai conversations; business automation workflows doubled while average task value declined from $49.30 to $47.90 as adoption broadened.

### Theoretical Foundations

**Eloundou et al. (2023), "GPTs are GPTs: An Early Look at the Labor Market Impact Potential of Large Language Models."** Introduces the beta framework AEDM inherits for theoretical exposure: tasks are rated on whether LLMs can complete them at 2x speed, where beta=1 indicates LLM alone, beta=0.5 with complementary tools, and beta=0 for infeasible tasks. Massenkoff & McCrory extended this framework using O\*NET task inventories.

### Empirical Context

**Brynjolfsson, Chandar & Chen (2025).** Combined AI task-level exposure measures with ADP employment data to estimate early labor market effects, providing some of the first large-scale empirical evidence connecting AI capability to employment outcomes.

**World Economic Forum (2025), Future of Jobs Report.** Found that 63% of employers cite skills gaps as the primary barrier to AI-driven transformation — the demand signal that motivates AEDM's reskilling urgency scoring.

### AEDM's Contribution

The literature establishes *that* AI exposure is distributed unevenly across occupations and demographics. What it does not provide is:

1. **Organizational-level measurement** — translating economy-wide SOC rates to a specific workforce
2. **Temporal tracking** — detecting whether exposure is accelerating within an organization over time
3. **Equity analysis at the organizational level** — testing whether macro demographic patterns hold within a specific role mix
4. **Actionable prioritization** — connecting measurement to workforce investment decisions via composite urgency scoring

AEDM addresses all four gaps, using statistical methods (CUSUM changepoint detection, permutation testing, composite scoring) that are appropriate for the short time series and moderate sample sizes typical of organizational workforce data.

---

## 1. Exposure Index Construction

### What It Measures

The exposure index quantifies how much of a given role's work *could be* and *is being* performed or augmented by AI. It produces a single score between 0 (no exposure) and 1 (fully exposed) for each role in the organization.

### How It Works

The index blends two components:

**Theoretical exposure** represents the fraction of an occupation's tasks that large language models could feasibly perform, based on O\*NET task-level analysis. This is derived from Anthropic's published research, which mapped Claude's capabilities against the detailed task inventories maintained by the U.S. Department of Labor's O\*NET system. A task is considered theoretically exposed if an LLM could perform it at a quality level sufficient for professional use, with or without human oversight.

**Observed exposure** represents the fraction of tasks actually being automated in practice, measured via real Claude usage data (the Anthropic Economic Index). This captures actual adoption patterns — what organizations are *choosing* to automate, not just what they *could* automate.

### The Composite Formula

```
exposure_index = (weight_theoretical × theoretical_rate) + (weight_observed × observed_rate)
```

Default weights: `weight_theoretical = 0.4`, `weight_observed = 0.6`.

Observed exposure is weighted more heavily because operational workforce planning should be grounded in what AI is actually doing, not just what it could theoretically do. Theoretical exposure is still included because it signals where adoption is likely to expand — the "uncovered area" identified in Anthropic's research.

### Granularity

Exposure rates are available at the SOC major group level (2-digit codes, 22 groups). Each role is mapped to its SOC major group, either via a user-provided SOC code or via automated fuzzy matching of the job title. This means all roles within the same SOC major group share the same reference rates, though the blended score can differ if custom weights are applied.

### Tier Assignment

| Tier | Score Range | Interpretation |
|------|-------------|----------------|
| Critical | 0.75 - 1.00 | Majority of tasks are AI-exposed; near-term workforce impact likely |
| High | 0.50 - 0.74 | Significant exposure; active monitoring and planning recommended |
| Moderate | 0.25 - 0.49 | Some tasks exposed; periodic review appropriate |
| Low | 0.00 - 0.24 | Limited AI exposure under current technology |

### Limitations

- SOC major group granularity may mask significant within-group variation. A "Software Developer" and a "Database Administrator" share SOC major group 15-0000 but may have different exposure profiles.
- Theoretical exposure estimates are based on current LLM capabilities and will shift as models improve.
- Observed exposure rates are calibrated to Anthropic's platform data and may not perfectly generalize to all AI tools.

---

## 2. Drift Detection

### What It Measures

Drift detection identifies whether a role's or department's AI exposure is changing over time — and specifically, whether there has been a statistically significant shift in the trend.

### Why CUSUM

We use CUSUM (Cumulative Sum Control Chart) for changepoint detection. CUSUM was originally developed for industrial quality control and is well-suited to detecting small, persistent shifts in a process mean — exactly the pattern we expect as AI adoption gradually accelerates in specific functions.

Alternative methods like PELT (Pruned Exact Linear Time) or Bayesian Online Changepoint Detection are more complex and require more data points. CUSUM works well with the short time series (4-12 quarters) typical of organizational workforce data.

### The Method

Given a time series of exposure scores $[x_1, x_2, \ldots, x_n]$:

1. Compute the series mean $\bar{x}$ as the baseline.
2. Compute the cumulative sum of deviations: $S_t = \sum_{i=1}^{t}(x_i - \bar{x})$
3. The CUSUM statistic is $\max(S_t) - \min(S_t)$.
4. The changepoint is estimated at the index where the maximum deviation from the cumulative sum occurs.

### Significance Testing

We assess significance via permutation testing:

1. Compute the CUSUM statistic for the observed series.
2. Randomly permute the series 1,000 times and recompute the CUSUM statistic for each permutation.
3. The p-value is the proportion of permuted statistics that exceed the observed statistic.
4. A changepoint is considered significant at $p < 0.05$.

This non-parametric approach makes no distributional assumptions about the exposure scores.

### Linear Trend

As a complement to changepoint detection, we also fit a simple linear trend via ordinary least squares:

```
exposure = β₀ + β₁ × time_index + ε
```

The slope $\beta_1$ estimates the rate of exposure change per period. A 95% confidence interval is provided. This is useful when the change is gradual rather than abrupt.

### Data Requirements

- **Minimum:** 3 time periods (changepoint detection is possible but power is limited)
- **Recommended:** 4+ time periods for reliable detection
- **Ideal:** 8+ quarterly observations for both changepoint and trend analysis

---

## 3. Demographic Disparity Analysis

### What It Measures

Disparity analysis identifies whether AI exposure falls disproportionately on specific demographic groups within the organization — by gender, education level, or pay band.

### Method

For each demographic segment (e.g., "Bachelor's degree holders" or "employees in the $80K-$120K pay band"):

1. **Exposure-weighted headcount:** $\sum_{\text{roles}} \text{headcount} \times \text{exposure\_score} \times \text{segment\_proportion}$
2. **Mean exposure:** The headcount-weighted average exposure score for all roles in the segment.
3. **Disparity ratio:** $\frac{\text{segment mean exposure}}{\text{org-wide mean exposure}}$

### Flagging

A segment is flagged when its disparity ratio exceeds **1.2x** — meaning workers in that segment face at least 20% more AI exposure than the organization average. This threshold is configurable.

### Context

Anthropic's research found that AI exposure systematically skews toward:
- **Female workers** — driven by high exposure in administrative, financial, and HR roles
- **More educated workers** — knowledge work tasks are more LLM-amenable
- **Higher-paid workers** — correlated with knowledge work concentration

AEDM surfaces whether these macro patterns hold within a specific organization, enabling targeted intervention.

### Limitations

- Disparity analysis depends on the demographic fields provided in the input data. If gender or salary data is unavailable, those dimensions are omitted.
- Disparity ratios describe correlation, not causation. A high ratio means more exposure, not that exposure *because of* demographic characteristics.

---

## 4. Reskilling Urgency Score

### What It Measures

The urgency score prioritizes which roles most need reskilling investment *right now*. It is a composite metric that accounts for not just how exposed a role is, but how fast that exposure is growing, how many people are affected, and how difficult the reskilling pathway would be.

### Components and Weights

| Component | Weight | Source | Description |
|-----------|--------|--------|-------------|
| Exposure level | 0.30 | `exposure.py` | Current blended exposure score |
| Drift velocity | 0.25 | `drift.py` | Rate of exposure change (trend slope, normalized) |
| Headcount at risk | 0.25 | Input data | Number of employees in the role, log-scaled and normalized |
| Reskill difficulty | 0.20 | Estimated | Proxy for how hard it is to transition to a lower-exposure role |

### Reskill Difficulty Estimation

Reskill difficulty is estimated as the "distance" in skill space between the current role's SOC group and the nearest SOC group with meaningfully lower exposure. This is a simplified proxy — a full skills-based transition analysis would require O\*NET skills and abilities data at the detailed occupation level.

The current implementation uses the difference in exposure rates as a proxy: if all nearby occupations are equally exposed, reskilling is harder because there are fewer safe harbors.

### Score Computation

```
urgency = (0.30 × exposure_norm) + (0.25 × drift_norm) + (0.25 × headcount_norm) + (0.20 × difficulty_norm)
```

All components are normalized to [0, 1] before weighting. If drift data is unavailable (single-period analysis), the drift component is set to 0 and the remaining weights are rescaled proportionally.

### Tier Assignment

| Tier | Score Range | Recommended Action |
|------|-------------|-------------------|
| Critical | 0.75 - 1.00 | Immediate reskilling program; role may be significantly restructured within 12-18 months |
| High | 0.50 - 0.74 | Active reskilling planning; begin skill gap assessments |
| Moderate | 0.25 - 0.49 | Monitor and include in next planning cycle |
| Low | 0.00 - 0.24 | No immediate action; periodic review |

---

## 5. Limitations

This section exists because honest methodology requires honest limitations.

- **SOC-level granularity:** Exposure rates are aggregated to SOC major groups (22 categories). This is a meaningful abstraction — a "Marketing Manager" and a "Construction Manager" are in the same major group (11-0000) despite very different AI exposure profiles. As more granular observed exposure data becomes available, AEDM can incorporate it.

- **Platform-specific calibration:** Observed exposure rates are derived from Anthropic's Claude usage data. Organizations using different AI tools may exhibit different adoption patterns. The theoretical rates (from O\*NET task analysis) are model-agnostic, but the observed rates are not.

- **Longitudinal data requirements:** Drift detection requires multiple time periods of workforce data. Many organizations are only beginning to track AI exposure, so the first analysis will often be a single-snapshot baseline. The tool is designed to grow more valuable over time as more data accumulates.

- **Reskill difficulty proxy:** The current difficulty estimate is a rough proxy based on exposure-rate distance. A full implementation would incorporate O\*NET skills taxonomies, local labor market data, and organizational training capacity.

- **Causal inference:** AEDM measures exposure and correlation, not causation. A high exposure score does not mean a role *will* be automated — it means a significant fraction of its tasks *could be* performed by current AI systems. Organizational context, regulatory constraints, and strategic choices all mediate the path from exposure to impact.

- **Static reference rates:** The Anthropic exposure rates are a snapshot from March 2026. As AI capabilities and adoption patterns evolve, these rates will need updating. AEDM is designed to accept updated reference data without code changes.
