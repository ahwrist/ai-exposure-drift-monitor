# Data Dictionary

This document defines all data fields used by AEDM, including input schemas, internal models, and output formats.

---

## Input Data

### Organization Roles (`acme_corp_roles.csv`)

The primary input file describing an organization's job architecture.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `role_id` | string | No | Auto-generated (`R001`, `R002`, ...) | Unique identifier for the role |
| `title` | string | **Yes** | — | Job title (used for SOC mapping if `soc_code` is absent) |
| `soc_code` | string | No | Auto-mapped via fuzzy match | O\*NET SOC code (6-digit, e.g., `15-1252`) |
| `department` | string | No | `"Unknown"` | Department or functional area |
| `headcount` | integer | No | `1` | Number of employees in this role |
| `gender_pct_female` | float | No | `null` | Proportion of role holders who are female (0.0 - 1.0) |
| `median_salary` | integer | No | `null` | Median annual salary in USD |
| `education_mode` | string | No | `null` | Most common education level. Valid values: `High School`, `Associate`, `Bachelor`, `Master`, `Doctorate` |
| `remote_pct` | float | No | `null` | Proportion of role eligible for remote work (0.0 - 1.0) |

### Quarterly Snapshots (`acme_corp_quarterly/q1_2025.csv`, etc.)

Same schema as the roles file above. Each file represents the organization's role architecture at a point in time. Used for drift detection.

Files should be named with a sortable period identifier (e.g., `q1_2025.csv`, `q2_2025.csv`). The tool sorts files lexicographically to determine temporal order.

### Reference Rates (`anthropic_exposure_rates.json`)

Pre-computed exposure rates by SOC major group, derived from Anthropic's published research.

| Field | Type | Description |
|-------|------|-------------|
| `metadata.source` | string | Citation for the source research |
| `metadata.retrieved` | string | Date the rates were extracted |
| `metadata.notes` | string | Additional context |
| `rates.<soc_code>.group_name` | string | SOC major group name |
| `rates.<soc_code>.theoretical_exposure` | float | Fraction of tasks AI could feasibly perform (0.0 - 1.0) |
| `rates.<soc_code>.observed_exposure` | float | Fraction of tasks actually being automated (0.0 - 1.0) |
| `rates.<soc_code>.coverage_gap` | float | `theoretical - observed` — the "uncovered area" |

---

## Internal Models

### Role

| Field | Type | Description |
|-------|------|-------------|
| `role_id` | string | Unique identifier |
| `title` | string | Job title |
| `soc_code` | string | Mapped SOC code |
| `soc_major_group` | string | First 2 digits of SOC code + `-0000` (e.g., `15-0000`) |
| `department` | string | Department name |
| `headcount` | int | Employee count |
| `gender_pct_female` | float \| None | Gender proportion |
| `median_salary` | int \| None | Median salary |
| `education_mode` | string \| None | Education level |
| `remote_pct` | float \| None | Remote proportion |

### ExposureScore

| Field | Type | Description |
|-------|------|-------------|
| `role_id` | string | Links to Role |
| `theoretical` | float | Theoretical exposure rate from reference data (0.0 - 1.0) |
| `observed` | float | Observed exposure rate from reference data (0.0 - 1.0) |
| `blended` | float | Weighted composite score (0.0 - 1.0) |
| `tier` | ExposureTier | `Critical` \| `High` \| `Moderate` \| `Low` |
| `soc_major_group` | string | SOC major group used for lookup |

### DriftResult

| Field | Type | Description |
|-------|------|-------------|
| `entity_id` | string | Role ID or department name being tracked |
| `direction` | DriftDirection | `Accelerating` \| `Stable` \| `Decelerating` |
| `magnitude` | float | CUSUM statistic value |
| `changepoint_index` | int \| None | Index in the time series where the shift was detected |
| `p_value` | float | Permutation test p-value |
| `trend_slope` | float | OLS slope (exposure change per period) |
| `trend_ci_lower` | float | 95% confidence interval lower bound |
| `trend_ci_upper` | float | 95% confidence interval upper bound |
| `n_periods` | int | Number of time periods analyzed |

### DemographicSegment

| Field | Type | Description |
|-------|------|-------------|
| `segment_type` | string | `gender` \| `education` \| `pay_band` |
| `segment_value` | string | Segment label (e.g., `"Female"`, `"Bachelor"`, `"$80K-$120K"`) |
| `mean_exposure` | float | Headcount-weighted mean exposure for this segment |
| `disparity_ratio` | float | `segment_mean / org_mean` — values > 1.2 are flagged |
| `headcount` | int | Total headcount in this segment |
| `exposure_weighted_headcount` | float | `headcount × mean_exposure` |
| `flagged` | bool | `True` if disparity_ratio > 1.2 |

### UrgencyScore

| Field | Type | Description |
|-------|------|-------------|
| `role_id` | string | Links to Role |
| `score` | float | Composite urgency score (0.0 - 1.0) |
| `tier` | ExposureTier | `Critical` \| `High` \| `Moderate` \| `Low` |
| `exposure_component` | float | Weighted exposure contribution |
| `drift_component` | float | Weighted drift contribution (0 if no drift data) |
| `headcount_component` | float | Weighted headcount contribution |
| `difficulty_component` | float | Weighted reskill difficulty contribution |

---

## Enumerations

### ExposureTier

| Value | Score Range |
|-------|-------------|
| `Critical` | 0.75 - 1.00 |
| `High` | 0.50 - 0.74 |
| `Moderate` | 0.25 - 0.49 |
| `Low` | 0.00 - 0.24 |

### RiskLevel

| Value | Description |
|-------|-------------|
| `Critical` | Immediate action required |
| `High` | Active planning needed |
| `Moderate` | Monitor and review |
| `Low` | No immediate concern |

### DriftDirection

| Value | Description |
|-------|-------------|
| `Accelerating` | Exposure is increasing over time (positive slope) |
| `Stable` | No significant change detected |
| `Decelerating` | Exposure is decreasing over time (negative slope) |

---

## Output Formats

### Report Export (CSV)

The `aedm analyze` command produces a CSV with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `role_id` | string | Role identifier |
| `title` | string | Job title |
| `department` | string | Department |
| `headcount` | int | Employee count |
| `soc_code` | string | Mapped SOC code |
| `theoretical_exposure` | float | Theoretical rate |
| `observed_exposure` | float | Observed rate |
| `blended_exposure` | float | Composite score |
| `exposure_tier` | string | Tier label |
| `urgency_score` | float | Reskilling urgency |
| `urgency_tier` | string | Urgency tier label |

### Report Export (JSON)

Structured JSON containing all computed models (`ExposureScore`, `DriftResult`, `DemographicSegment`, `UrgencyScore`) keyed by role ID, plus org-wide summary statistics.
