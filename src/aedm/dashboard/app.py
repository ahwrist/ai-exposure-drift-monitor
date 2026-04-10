"""Streamlit interactive dashboard for AEDM."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from aedm.analysis.demographics import (
    analyze_all_disparities,
    analyze_intersectional_disparities,
)
from aedm.analysis.drift import detect_org_drift
from aedm.analysis.exposure import (
    compute_org_exposure,
    exposure_by_department,
    org_mean_exposure,
)
from aedm.analysis.reskill import score_org_urgency
from aedm.config import settings
from aedm.ingest.parser import load_quarterly_snapshots, load_reference_rates, parse_csv
from aedm.models.enums import ExposureTier
from aedm.output.charts import (
    demographic_disparity_bars,
    drift_sparklines,
    exposure_distribution,
    exposure_heatmap,
    urgency_matrix,
)
from aedm.output.export import scores_to_dataframe

# Page config
st.set_page_config(
    page_title="AEDM — AI Exposure Drift Monitor",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def load_raw_data(
    input_path: str,
    reference_path: str,
) -> tuple:  # type: ignore[type-arg]
    """Load raw roles and reference rates (weight-independent)."""
    roles = parse_csv(Path(input_path))
    rates = load_reference_rates(Path(reference_path))
    return roles, rates


@st.cache_data
def compute_analysis(
    input_path: str,
    reference_path: str,
    weight_theoretical: float = 0.4,
) -> tuple:  # type: ignore[type-arg]
    """Compute all analysis data with given weights."""
    roles, rates = load_raw_data(input_path, reference_path)
    weight_observed = 1.0 - weight_theoretical
    scores = compute_org_exposure(roles, rates, weight_theoretical, weight_observed)
    mean_exp = org_mean_exposure(roles, scores)
    dept_exp = exposure_by_department(roles, scores)
    urgency = score_org_urgency(roles, scores, None, rates)
    segments = analyze_all_disparities(roles, scores)
    return roles, rates, scores, mean_exp, dept_exp, urgency, segments


@st.cache_data
def load_drift_data(
    quarterly_dir: str,
    reference_path: str,
) -> list | None:  # type: ignore[type-arg]
    """Load quarterly snapshots and compute drift results."""
    try:
        snapshots = load_quarterly_snapshots(Path(quarterly_dir))
        rates = load_reference_rates(Path(reference_path))
    except (FileNotFoundError, Exception):
        return None

    dept_series: dict[str, list[float]] = {}
    for snapshot in snapshots:
        scores = compute_org_exposure(snapshot.roles, rates)
        dept_exp = exposure_by_department(snapshot.roles, scores)
        for dept, mean in dept_exp.items():
            if dept not in dept_series:
                dept_series[dept] = []
            dept_series[dept].append(mean)

    drift_results = detect_org_drift(dept_series)
    return drift_results


def main() -> None:
    """Main dashboard application."""
    st.title("📊 AI Exposure Drift Monitor")
    st.markdown("*Measurement-first AI workforce intelligence*")

    # Determine input paths
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        reference_path = sys.argv[2] if len(sys.argv) > 2 else str(settings.reference_rates_path)
    else:
        input_path = str(Path("data/sample/acme_corp_roles.csv"))
        reference_path = str(settings.reference_rates_path)

    # Sidebar
    st.sidebar.header("Configuration")
    input_path = st.sidebar.text_input("Data file", value=input_path)
    reference_path = st.sidebar.text_input("Reference rates", value=reference_path)

    try:
        roles_initial, _rates_initial = load_raw_data(input_path, reference_path)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    # Department filter
    departments = sorted(set(r.department for r in roles_initial))
    selected_depts = st.sidebar.multiselect("Filter departments", departments, default=departments)

    # Weight tuning
    with st.sidebar.expander("Advanced: Adjust Weights"):
        weight_theoretical = st.slider(
            "Theoretical weight",
            min_value=0.0,
            max_value=1.0,
            value=0.4,
            step=0.05,
        )
        weight_observed = 1.0 - weight_theoretical
        st.markdown(f"**Observed weight:** {weight_observed:.2f}")
        st.caption(
            "Higher observed weight = more grounded in actual AI adoption. "
            "Higher theoretical weight = more forward-looking."
        )

    # Compute analysis with current weights
    try:
        roles, rates, scores, mean_exp, dept_exp, urgency, segments = compute_analysis(
            input_path, reference_path, weight_theoretical
        )
    except Exception as e:
        st.error(f"Error computing analysis: {e}")
        return

    score_map = {s.role_id: s for s in scores}

    # About AEDM sidebar section
    st.sidebar.divider()
    st.sidebar.subheader("About AEDM")
    st.sidebar.markdown(
        "Built on Anthropic's *Labor Market Impacts of AI* framework "
        "(Massenkoff & McCrory, March 2026)"
    )
    st.sidebar.markdown(
        "[Read the research](https://www.anthropic.com/research/labor-market-impacts)"
    )
    st.sidebar.caption(
        "Statistical methods: CUSUM changepoint detection, permutation testing, composite scoring"
    )
    st.sidebar.caption(
        "\u2696\ufe0f This tool measures exposure and correlation, not causation. "
        "See the Demographics tab for responsible use guidance."
    )

    filtered_roles = [r for r in roles if r.department in selected_depts]
    filtered_scores = [s for s in scores if any(r.role_id == s.role_id for r in filtered_roles)]

    # Load drift data (used by both Drift Analysis and Scenario tabs)
    quarterly_dir = str(Path("data/sample/acme_corp_quarterly"))
    drift_results = load_drift_data(quarterly_dir, reference_path)

    # Tabs
    tab1, tab_how, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "Org Overview",
            "Research Foundation",
            "Exposure Heatmap",
            "Drift Analysis",
            "Demographics",
            "Reskilling Priority",
            "Scenario",
        ]
    )

    # Tab 1: Org Overview
    with tab1:
        total_hc = sum(r.headcount for r in filtered_roles)
        weighted_sum = sum(
            score_map[r.role_id].blended * r.headcount
            for r in filtered_roles
            if r.role_id in score_map
        )
        filtered_mean = weighted_sum / total_hc if total_hc > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Roles", len(filtered_roles))
        col2.metric("Total Headcount", f"{total_hc:,}")
        col3.metric("Mean Exposure", f"{filtered_mean:.1%}")

        # Highest risk department
        if dept_exp:
            top_dept = max(
                ((d, v) for d, v in dept_exp.items() if d in selected_depts),
                key=lambda x: x[1],
                default=("N/A", 0),
            )
            col4.metric("Highest Risk Dept", top_dept[0], f"{top_dept[1]:.1%}")

        # Compute theoretical-observed gap for narrative
        theo_sum = sum(
            score_map[r.role_id].theoretical * r.headcount
            for r in filtered_roles
            if r.role_id in score_map
        )
        obs_sum = sum(
            score_map[r.role_id].observed * r.headcount
            for r in filtered_roles
            if r.role_id in score_map
        )
        theo_mean = theo_sum / total_hc if total_hc > 0 else 0
        obs_mean = obs_sum / total_hc if total_hc > 0 else 0
        gap_points = theo_mean - obs_mean

        top_dept_name = top_dept[0] if dept_exp else "N/A"
        top_dept_score = top_dept[1] if dept_exp else 0

        st.markdown(
            f"Across your **{len(filtered_roles)} roles** ({total_hc:,} employees), "
            f"AEDM identifies a mean blended exposure of **{filtered_mean:.1%}**. "
            f"The gap between theoretical and observed exposure averages "
            f"**{gap_points:.0%} points** \u2014 consistent with Massenkoff & McCrory's "
            f"finding that actual AI adoption remains a fraction of theoretical capability. "
            f"**{top_dept_name}** faces the highest departmental exposure "
            f"at {top_dept_score:.1%}."
        )

        # Determine tier label for the expander
        if filtered_mean >= 0.75:
            tier_label = "Critical"
        elif filtered_mean >= 0.50:
            tier_label = "High"
        elif filtered_mean >= 0.25:
            tier_label = "Moderate"
        else:
            tier_label = "Low"

        with st.expander("What This Means"):
            st.markdown(
                f"A mean exposure of {filtered_mean:.1%} places your organization in the "
                f"**{tier_label}** range. The {gap_points:.0%}-point theoretical-observed "
                f"gap suggests significant latent automation potential. As AI adoption "
                f"accelerates \u2014 which Anthropic's Economic Index shows is happening "
                f"via learning curves and broadening use cases \u2014 roles currently at "
                f"Moderate exposure may cross into High within 2\u20134 quarters."
            )

        st.plotly_chart(exposure_distribution(filtered_scores), use_container_width=True)

        # Top 10 most exposed roles
        st.subheader("Top 10 Most Exposed Roles")
        top_roles = sorted(filtered_scores, key=lambda s: s.blended, reverse=True)[:10]
        role_map = {r.role_id: r for r in filtered_roles}
        top_data = []
        for s in top_roles:
            r = role_map.get(s.role_id)
            if r:
                top_data.append(
                    {
                        "Title": r.title,
                        "Department": r.department,
                        "Exposure": f"{s.blended:.1%}",
                        "Tier": s.tier.value,
                        "Headcount": r.headcount,
                    }
                )
        if top_data:
            st.dataframe(pd.DataFrame(top_data), use_container_width=True, hide_index=True)

        # Export
        export_df = scores_to_dataframe(filtered_roles, filtered_scores)
        st.download_button(
            "Download Exposure Scores (CSV)",
            data=export_df.to_csv(index=False),
            file_name="exposure_scores.csv",
            mime="text/csv",
        )

    # Tab: Research Foundation
    with tab_how:
        st.subheader("Research Question")
        st.markdown(
            "> *At the organizational level, how is the gap between theoretical AI "
            "capability and actual adoption distributed across roles, departments, "
            "and demographic segments \u2014 and how can organizations detect when "
            "that gap is closing before displacement becomes visible?*"
        )
        st.markdown(
            "Massenkoff & McCrory (2026) established the macro framework: theoretical "
            "AI exposure (what LLMs *could* do, per Eloundou et al.'s beta ratings of "
            "O\\*NET tasks) far exceeds observed adoption (what organizations *are* "
            "automating, measured via the Anthropic Economic Index). Across all 22 SOC "
            "major groups, 97% of observed Claude tasks fall into categories rated as "
            "theoretically feasible \u2014 yet actual coverage remains far below "
            "theoretical ceilings."
        )

        st.subheader("What AEDM Adds Beyond the Paper")
        st.markdown(
            "1. **Macro \u2192 Organizational translation.** The paper provides "
            "economy-wide exposure rates by SOC code. AEDM maps *your* specific roles "
            "to that framework.\n"
            "2. **Snapshot \u2192 Temporal tracking.** The paper is cross-sectional. "
            "AEDM adds drift detection \u2014 are your exposure rates accelerating, "
            "decelerating, or stable quarter over quarter?\n"
            "3. **Aggregate \u2192 Equity lens.** The paper shows macro-level "
            "demographic skew (16pp more female, 47% higher-earning). AEDM tests "
            "whether *your* org replicates or departs from those patterns.\n"
            "4. **Measurement \u2192 Action.** The paper measures; AEDM prescribes. "
            "Composite urgency scoring connects exposure to workforce investment "
            "decisions."
        )

        st.markdown("---")
        st.subheader("AI Exposure by Occupation (Reference Data)")

        # Load reference rates for the grouped bar chart
        ref_path = Path(reference_path)
        with open(ref_path) as f:
            ref_data = json.load(f)

        ref_rows = []
        for _soc, entry in ref_data["rates"].items():
            ref_rows.append(
                {
                    "group": entry["group_name"],
                    "theoretical": entry["theoretical_exposure"],
                    "observed": entry["observed_exposure"],
                    "gap": entry["coverage_gap"],
                }
            )
        ref_df = pd.DataFrame(ref_rows).sort_values("theoretical", ascending=True)

        fig_ref = go.Figure()
        fig_ref.add_trace(
            go.Bar(
                y=ref_df["group"],
                x=ref_df["theoretical"],
                name="Theoretical Exposure",
                orientation="h",
                marker_color="#3b82f6",
            )
        )
        fig_ref.add_trace(
            go.Bar(
                y=ref_df["group"],
                x=ref_df["observed"],
                name="Observed Exposure",
                orientation="h",
                marker_color="#14b8a6",
            )
        )
        fig_ref.add_trace(
            go.Bar(
                y=ref_df["group"],
                x=ref_df["gap"],
                name="Coverage Gap",
                orientation="h",
                marker_color="#fbbf24",
                opacity=0.7,
            )
        )
        fig_ref.update_layout(
            barmode="group",
            title="All 22 SOC Major Groups: Theoretical vs. Observed AI Exposure",
            xaxis_title="Exposure Rate",
            yaxis_title="",
            height=700,
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
            margin={"l": 300},
        )
        st.plotly_chart(fig_ref, use_container_width=True)

        st.caption(
            "Source: Massenkoff & McCrory (2026), derived from O\\*NET task inventories "
            "and the Anthropic Economic Index."
        )

        with st.expander("Anthropic Economic Index Context"):
            st.markdown(
                "The Anthropic Economic Index (March 2026) provides the real-world usage "
                "data that grounds AEDM's 'observed' exposure rates:\n\n"
                "- High-tenure users (6+ months) show **10% higher success rate** and are "
                "7pp more likely to use Claude for work\n"
                "- Computer and Mathematical occupations account for **35%** of Claude.ai "
                "conversations\n"
                "- For every $10 hourly wage increase: **1.5pp rise** in high-capability "
                "model usage\n"
                "- Business automation workflows **doubled**; average task value declined "
                "from $49.30 to $47.90 as adoption broadened\n\n"
                "These learning curves mean adoption is accelerating, making drift "
                "detection increasingly critical."
            )

        with st.expander("How We Operationalize the Research"):
            st.markdown(
                "**Exposure Index (40/60 Weighting):** The blended exposure score weights "
                "theoretical exposure at 40% and observed exposure at 60%. Observed is "
                "weighted more heavily because workforce planning should be grounded in "
                "actual AI adoption, not just what's theoretically possible. Theoretical "
                "exposure is still included because it signals where adoption is likely "
                "to expand."
            )
            st.markdown(
                "**CUSUM Drift Detection:** AEDM uses Cumulative Sum (CUSUM) control charts "
                "to detect changepoints in exposure trends over time. CUSUM excels at "
                "detecting small, persistent shifts \u2014 exactly the pattern expected as AI "
                "adoption gradually accelerates. Significance is assessed via permutation "
                "testing (1,000 permutations, p < 0.05)."
            )
            st.markdown(
                "**Urgency Scoring:** Reskilling urgency is a composite of four factors: "
                "current exposure level (30%), drift velocity (25%), headcount at risk "
                "(25%), and reskill difficulty (20%). This ensures that roles are not "
                "prioritized on exposure alone \u2014 a highly-exposed role with 2 employees "
                "ranks differently than one with 200."
            )

        st.markdown("---")
        st.subheader("Data Pipeline")
        st.code(
            "Your CSV  -->  SOC Mapping  -->  Exposure Scoring  "
            "-->  Drift Detection  -->  Demographics  -->  Urgency Rankings",
            language=None,
        )

    # Tab 2: Exposure Heatmap
    with tab2:
        st.subheader("Department × Role Exposure")
        metric_choice = st.radio(
            "Exposure metric",
            ["Blended", "Theoretical", "Observed"],
            horizontal=True,
        )
        fig = exposure_heatmap(filtered_roles, filtered_scores, metric=metric_choice.lower())
        st.plotly_chart(fig, use_container_width=True)

    # Tab 3: Drift Analysis
    with tab3:
        st.subheader("Exposure Drift Detection")

        if drift_results is None:
            st.info(
                "Drift analysis requires multi-period data. "
                "Use `aedm drift --input-dir quarterly_snapshots/` for full analysis."
            )
        else:
            # Dynamic narrative summary
            n_depts = len(drift_results)
            n_periods = drift_results[0].n_periods if drift_results else 0
            sig_drifts = [dr for dr in drift_results if dr.direction.value != "Stable"]
            accel_depts = [dr for dr in drift_results if dr.direction.value == "Accelerating"]
            accel_names = ", ".join(dr.entity_id for dr in accel_depts)

            st.markdown(
                f"Of **{n_depts} departments** tracked across **{n_periods} quarterly "
                f"snapshots**, **{len(sig_drifts)}** show statistically significant drift "
                f"(p < 0.05)."
                + (
                    f" **{accel_names}** "
                    f"{'is' if len(accel_depts) == 1 else 'are'} accelerating "
                    f"\u2014 meaning exposure is increasing faster than baseline. "
                    "This is the early-warning signal Massenkoff & McCrory's framework "
                    "is designed to detect."
                    if accel_depts
                    else ""
                )
            )

            fig = drift_sparklines(drift_results)
            st.plotly_chart(fig, use_container_width=True)

            drift_table = []
            for dr in sorted(drift_results, key=lambda d: abs(d.trend_slope), reverse=True):
                direction = dr.direction.value
                if direction == "Accelerating":
                    color = "🔴"
                elif direction == "Decelerating":
                    color = "🟢"
                else:
                    color = "⚪"
                drift_table.append(
                    {
                        "Department": dr.entity_id,
                        "Direction": f"{color} {direction}",
                        "Trend Slope": f"{dr.trend_slope:+.4f}",
                        "p-value": f"{dr.p_value:.3f}",
                        "Periods": dr.n_periods,
                    }
                )
            if drift_table:
                st.dataframe(
                    pd.DataFrame(drift_table),
                    use_container_width=True,
                    hide_index=True,
                )

            if sig_drifts:
                dept_names = ", ".join(dr.entity_id for dr in sig_drifts)
                st.warning(f"{len(sig_drifts)} department(s) show significant drift: {dept_names}")

            with st.expander("Why Drift Matters"):
                st.markdown(
                    "The original research found that hiring of 22\u201325 year olds in "
                    "exposed occupations slowed by approximately **14%** after ChatGPT's "
                    "launch \u2014 but this only became visible in retrospective analysis. "
                    "Drift detection aims to surface these shifts in **near-real-time** at "
                    "the organizational level, giving workforce planners the lead time to "
                    "act before displacement becomes visible in headcount data."
                )

            with st.expander("How Drift Detection Works"):
                st.markdown(
                    "AEDM uses **CUSUM (Cumulative Sum) changepoint detection** to identify "
                    "shifts in exposure trends over time. Statistical significance is assessed "
                    "via **permutation testing** \u2014 the observed CUSUM statistic is "
                    "compared against a null distribution of 1,000 random permutations. A "
                    "**linear trend slope** quantifies the rate of exposure change per period."
                )

    # Tab 4: Demographics
    with tab4:
        st.subheader("Demographic Disparity Analysis")
        st.markdown(
            "Massenkoff & McCrory found that high-exposure workers are **16 percentage "
            "points more likely female**, hold graduate degrees at nearly **4x the rate** "
            "of unexposed workers, and earn **47% more**. The question for *your* "
            "organization: does your exposure distribution replicate these macro patterns, "
            "or does your specific role mix create different equity dynamics?"
        )

        analysis_mode = st.radio(
            "Analysis mode",
            ["Single Dimension", "Intersectional"],
            horizontal=True,
        )

        if analysis_mode == "Single Dimension":
            if segments:
                flagged = [s for s in segments if s.flagged]
                if flagged:
                    st.warning(f"{len(flagged)} segment(s) flagged for disproportionate exposure.")
                else:
                    st.success("No segments exceed the disparity threshold.")

                fig = demographic_disparity_bars(segments)
                st.plotly_chart(fig, use_container_width=True)

                seg_df = pd.DataFrame(
                    [
                        {
                            "Type": s.segment_type.replace("_", " ").title(),
                            "Segment": s.segment_value,
                            "Mean Exposure": f"{s.mean_exposure:.1%}",
                            "Disparity Ratio": f"{s.disparity_ratio:.2f}x",
                            "Headcount": s.headcount,
                            "Flagged": "\u26a0\ufe0f" if s.flagged else "",
                        }
                        for s in segments
                    ]
                )
                st.dataframe(seg_df, use_container_width=True, hide_index=True)
        else:
            st.markdown(
                "Intersectional analysis reveals whether exposure disparities compound "
                "across demographic dimensions. For example, if both female workers and "
                "highly-educated workers face elevated exposure, do female workers with "
                "graduate degrees face even higher exposure than either dimension alone "
                "would predict?"
            )
            dimension_pair = st.selectbox(
                "Dimension pair",
                [
                    "Gender \u00d7 Education",
                    "Gender \u00d7 Pay Band",
                    "Education \u00d7 Pay Band",
                ],
            )
            pair_map: dict[str, tuple[str, str]] = {
                "Gender \u00d7 Education": ("gender", "education"),
                "Gender \u00d7 Pay Band": ("gender", "pay_band"),
                "Education \u00d7 Pay Band": ("education", "pay_band"),
            }
            dim_a, dim_b = pair_map[dimension_pair]
            intersectional_segments = analyze_intersectional_disparities(
                filtered_roles, filtered_scores, dim_a, dim_b
            )
            if intersectional_segments:
                flagged_ix = [s for s in intersectional_segments if s.flagged]
                if flagged_ix:
                    st.warning(
                        f"{len(flagged_ix)} intersectional segment(s) flagged "
                        "for disproportionate exposure."
                    )
                else:
                    st.success("No intersectional segments exceed the disparity threshold.")

                fig = demographic_disparity_bars(
                    intersectional_segments,
                    title=f"Intersectional Disparity: {dimension_pair}",
                )
                st.plotly_chart(fig, use_container_width=True)

                ix_df = pd.DataFrame(
                    [
                        {
                            "Segment": s.segment_value,
                            "Mean Exposure": f"{s.mean_exposure:.1%}",
                            "Disparity Ratio": f"{s.disparity_ratio:.2f}x",
                            "Headcount": s.headcount,
                            "Flagged": "\u26a0\ufe0f" if s.flagged else "",
                        }
                        for s in intersectional_segments
                    ]
                )
                st.dataframe(ix_df, use_container_width=True, hide_index=True)
            else:
                st.info(
                    "No intersectional segments meet the minimum headcount threshold (5). "
                    "This can happen with small datasets or narrow filters."
                )

        with st.expander("Responsible Use & Limitations"):
            st.markdown(
                "Disparity ratios describe **correlation, not causation**. A high ratio "
                "means a demographic segment faces more AI-exposed roles \u2014 not that "
                "demographic characteristics cause exposure."
            )
            st.markdown(
                "AEDM operates on **role-level aggregates**, not individual employee data. "
                "No PII is stored or processed."
            )
            st.markdown(
                "These findings should **inform planning conversations**, not determine "
                "individual employment outcomes."
            )

        # Export
        if segments:
            disparity_df = pd.DataFrame(
                [
                    {
                        "Segment Type": s.segment_type,
                        "Segment Value": s.segment_value,
                        "Mean Exposure": s.mean_exposure,
                        "Disparity Ratio": s.disparity_ratio,
                        "Headcount": s.headcount,
                        "Flagged": s.flagged,
                    }
                    for s in segments
                ]
            )
            st.download_button(
                "Download Disparity Analysis (CSV)",
                data=disparity_df.to_csv(index=False),
                file_name="disparity_analysis.csv",
                mime="text/csv",
            )

    # Tab 5: Reskilling Priority
    with tab5:
        st.subheader("Reskilling Urgency Rankings")

        st.markdown("**Why Composite Scoring, Not Just Exposure**")
        st.markdown(
            "A role with 90% exposure and 3 employees requires different intervention "
            "than one with 60% exposure and 300 employees whose exposure is accelerating. "
            "AEDM's urgency score weights four factors because workforce investment "
            "decisions are resource-constrained \u2014 the goal is to identify where "
            "reskilling investment has the highest expected impact."
        )
        st.info(
            "Urgency combines four factors: current exposure (30%), drift velocity (25%), "
            "headcount at risk (25%), and reskill difficulty (20%). Roles in the upper-right "
            "quadrant face both high exposure and high urgency."
        )

        fig = urgency_matrix(filtered_roles, filtered_scores, urgency)
        st.plotly_chart(fig, use_container_width=True)

        urg_data = []
        for u in urgency[:30]:
            r = {r_.role_id: r_ for r_ in roles}.get(u.role_id)
            if r and r.department in selected_depts:
                urg_data.append(
                    {
                        "Title": r.title,
                        "Department": r.department,
                        "Urgency Score": f"{u.score:.1%}",
                        "Tier": u.tier.value,
                        "Headcount": r.headcount,
                    }
                )
        if urg_data:
            st.dataframe(pd.DataFrame(urg_data), use_container_width=True, hide_index=True)

        # Export
        role_map_urg = {r.role_id: r for r in roles}
        urgency_df = pd.DataFrame(
            [
                {
                    "Title": role_map_urg[u.role_id].title if u.role_id in role_map_urg else "",
                    "Department": role_map_urg[u.role_id].department
                    if u.role_id in role_map_urg
                    else "",
                    "Urgency Score": u.score,
                    "Tier": u.tier.value,
                    "Headcount": role_map_urg[u.role_id].headcount
                    if u.role_id in role_map_urg
                    else 0,
                    "Exposure Component": u.exposure_component,
                    "Drift Component": u.drift_component,
                    "Headcount Component": u.headcount_component,
                    "Difficulty Component": u.difficulty_component,
                }
                for u in urgency
            ]
        )
        st.download_button(
            "Download Urgency Rankings (CSV)",
            data=urgency_df.to_csv(index=False),
            file_name="urgency_rankings.csv",
            mime="text/csv",
        )

    # Tab 6: Scenario Modeling
    with tab6:
        st.subheader("What-If Scenario: Exposure Acceleration")
        st.info(
            "The gap between theoretical and observed exposure averages 50-65 percentage "
            "points across occupations. This scenario models what happens as that gap narrows."
        )
        st.markdown(
            "Model what happens if observed exposure catches up to a given "
            "percentage of theoretical exposure."
        )

        catch_up_pct = st.slider(
            "Observed exposure catches up to X% of theoretical",
            min_value=10,
            max_value=100,
            value=50,
            step=5,
        )

        scenario_factor = catch_up_pct / 100.0

        # Recompute with scenario rates
        scenario_scores = []
        for s in scores:
            gap = s.theoretical - s.observed
            new_observed = s.observed + gap * scenario_factor
            new_blended = weight_theoretical * s.theoretical + weight_observed * new_observed
            new_tier = ExposureTier.from_score(new_blended)
            scenario_scores.append(
                {
                    "role_id": s.role_id,
                    "current_blended": s.blended,
                    "scenario_blended": new_blended,
                    "change": new_blended - s.blended,
                    "current_tier": s.tier.value,
                    "scenario_tier": new_tier.value,
                }
            )

        scenario_df = pd.DataFrame(scenario_scores)
        role_lookup = {r.role_id: r for r in roles}

        # Summary metrics
        current_mean = scenario_df["current_blended"].mean()
        scenario_mean = scenario_df["scenario_blended"].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Current Mean Exposure", f"{current_mean:.1%}")
        delta = scenario_mean - current_mean
        col2.metric("Scenario Mean Exposure", f"{scenario_mean:.1%}", f"+{delta:.1%}")

        current_critical = (scenario_df["current_tier"] == "Critical").sum()
        scenario_critical = (scenario_df["scenario_tier"] == "Critical").sum()
        crit_delta = scenario_critical - current_critical
        col3.metric("Critical-Tier Roles", scenario_critical, f"+{crit_delta}")

        # Show biggest movers
        scenario_df["title"] = scenario_df["role_id"].map(lambda x: role_lookup.get(x))
        scenario_df["title"] = scenario_df["title"].apply(lambda r: r.title if r else "")
        scenario_df = scenario_df.sort_values("change", ascending=False)

        st.subheader("Biggest Impact Roles")
        cols = ["title", "current_blended", "scenario_blended", "change", "scenario_tier"]
        display_df = scenario_df.head(15)[cols]
        display_df.columns = ["Title", "Current", "Scenario", "Change", "New Tier"]
        display_df["Current"] = display_df["Current"].apply(lambda x: f"{x:.1%}")
        display_df["Scenario"] = display_df["Scenario"].apply(lambda x: f"{x:.1%}")
        display_df["Change"] = display_df["Change"].apply(lambda x: f"+{x:.1%}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # --- Scenario 2: Time-to-Critical Projection ---
        st.markdown("---")
        st.subheader("Time-to-Critical Projection")
        st.markdown(
            "Using drift slopes from quarterly data, project how many quarters "
            "until each department crosses the **Critical (0.75)** threshold."
        )

        if drift_results is not None and drift_results:
            critical_threshold = 0.75
            projection_rows = []
            projected_count = 0
            for dr in sorted(drift_results, key=lambda d: d.trend_slope, reverse=True):
                dept_current = dept_exp.get(dr.entity_id, 0.0)
                if dr.trend_slope > 0 and dept_current < critical_threshold:
                    remaining = critical_threshold - dept_current
                    quarters = remaining / dr.trend_slope
                    confidence = "High" if dr.p_value < 0.05 else "Low"
                    projection_rows.append(
                        {
                            "Department": dr.entity_id,
                            "Current Exposure": f"{dept_current:.1%}",
                            "Drift Slope": f"{dr.trend_slope:+.4f}",
                            "Quarters to Critical": f"{quarters:.1f}",
                            "Confidence": confidence,
                        }
                    )
                    projected_count += 1
                elif dept_current >= critical_threshold:
                    projection_rows.append(
                        {
                            "Department": dr.entity_id,
                            "Current Exposure": f"{dept_current:.1%}",
                            "Drift Slope": f"{dr.trend_slope:+.4f}",
                            "Quarters to Critical": "Already Critical",
                            "Confidence": "—",
                        }
                    )
                else:
                    projection_rows.append(
                        {
                            "Department": dr.entity_id,
                            "Current Exposure": f"{dept_current:.1%}",
                            "Drift Slope": f"{dr.trend_slope:+.4f}",
                            "Quarters to Critical": "Not projected",
                            "Confidence": "—",
                        }
                    )

            if projected_count > 0:
                st.markdown(
                    f"At current drift rates, **{projected_count} department(s)** are "
                    "projected to reach Critical exposure."
                )
            else:
                st.info("No departments are currently projected to reach Critical exposure.")

            if projection_rows:
                st.dataframe(
                    pd.DataFrame(projection_rows),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info(
                "Time-to-critical projections require multi-period drift data. "
                "Load quarterly snapshots to enable this scenario."
            )

        # --- Scenario 3: Reskilling Impact Simulation ---
        st.markdown("---")
        st.subheader("Reskilling Impact Simulation")
        st.markdown(
            "Reskilling is not about eliminating exposure \u2014 it's about ensuring your "
            "workforce can work **with** AI effectively, reducing the risk that exposure "
            "translates to displacement."
        )

        reskill_pct = st.slider(
            "Reskill top N% of highest-urgency roles",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
        )
        reskill_reduction = st.slider(
            "Exposure reduction from reskilling (%)",
            min_value=10,
            max_value=50,
            value=30,
            step=5,
        )

        reduction_factor = reskill_reduction / 100.0
        n_to_reskill = max(1, int(len(urgency) * reskill_pct / 100))
        top_urgency_ids = {u.role_id for u in urgency[:n_to_reskill]}

        # Compute before/after
        before_total_hc = 0
        before_weighted = 0.0
        after_weighted = 0.0
        before_tiers: dict[str, int] = {}
        after_tiers: dict[str, int] = {}

        for role in filtered_roles:
            score = score_map.get(role.role_id)
            if score is None:
                continue
            before_total_hc += role.headcount
            before_weighted += score.blended * role.headcount

            if role.role_id in top_urgency_ids:
                new_blended = score.blended * (1 - reduction_factor)
            else:
                new_blended = score.blended
            after_weighted += new_blended * role.headcount

            before_tier = ExposureTier.from_score(score.blended).value
            after_tier = ExposureTier.from_score(new_blended).value
            before_tiers[before_tier] = before_tiers.get(before_tier, 0) + 1
            after_tiers[after_tier] = after_tiers.get(after_tier, 0) + 1

        before_mean = before_weighted / before_total_hc if before_total_hc > 0 else 0
        after_mean = after_weighted / before_total_hc if before_total_hc > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Roles Reskilled", n_to_reskill)
        col2.metric("Before Mean Exposure", f"{before_mean:.1%}")
        reskill_delta = after_mean - before_mean
        col3.metric("After Mean Exposure", f"{after_mean:.1%}", f"{reskill_delta:.1%}")

        # Tier distribution comparison
        tier_comparison = []
        for tier_name in ["Critical", "High", "Moderate", "Low"]:
            tier_comparison.append(
                {
                    "Tier": tier_name,
                    "Before": before_tiers.get(tier_name, 0),
                    "After": after_tiers.get(tier_name, 0),
                    "Change": after_tiers.get(tier_name, 0) - before_tiers.get(tier_name, 0),
                }
            )
        st.dataframe(
            pd.DataFrame(tier_comparison),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()
