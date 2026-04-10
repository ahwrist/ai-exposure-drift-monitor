"""Streamlit interactive dashboard for AEDM."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from aedm.analysis.demographics import analyze_all_disparities
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

# Page config
st.set_page_config(
    page_title="AEDM — AI Exposure Drift Monitor",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def load_data(
    input_path: str,
    reference_path: str,
) -> tuple:  # type: ignore[type-arg]
    """Load and compute all analysis data."""
    roles = parse_csv(Path(input_path))
    rates = load_reference_rates(Path(reference_path))
    scores = compute_org_exposure(roles, rates)
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
        roles, rates, scores, mean_exp, dept_exp, urgency, segments = load_data(
            input_path, reference_path
        )
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    score_map = {s.role_id: s for s in scores}
    # Department filter
    departments = sorted(set(r.department for r in roles))
    selected_depts = st.sidebar.multiselect("Filter departments", departments, default=departments)

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
        "Statistical methods: CUSUM changepoint detection, "
        "permutation testing, composite scoring"
    )
    st.sidebar.caption(
        "\u2696\ufe0f This tool measures exposure and correlation, not causation. "
        "See the Demographics tab for responsible use guidance."
    )

    filtered_roles = [r for r in roles if r.department in selected_depts]
    filtered_scores = [s for s in scores if any(r.role_id == s.role_id for r in filtered_roles)]

    # Tabs
    tab1, tab_how, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "Org Overview",
            "How It Works",
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

        st.info(
            "Anthropic's March 2026 research found that theoretical AI exposure far exceeds "
            "observed adoption. The 'uncovered area' between these rates signals where AI "
            "adoption is likely to accelerate. "
            "[Source: Massenkoff & McCrory, 2026]"
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

    # Tab: How It Works
    with tab_how:
        st.subheader("Research Foundation: AI Exposure by Occupation")

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

        with st.expander("Methodology Details"):
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
                "detecting small, persistent shifts — exactly the pattern expected as AI "
                "adoption gradually accelerates. Significance is assessed via permutation "
                "testing (1,000 permutations, p < 0.05)."
            )
            st.markdown(
                "**Urgency Scoring:** Reskilling urgency is a composite of four factors: "
                "current exposure level (30%), drift velocity (25%), headcount at risk "
                "(25%), and reskill difficulty (20%). This ensures that roles are not "
                "prioritized on exposure alone — a highly-exposed role with 2 employees "
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
        st.radio(
            "Exposure metric",
            ["Blended", "Theoretical", "Observed"],
            horizontal=True,
        )
        fig = exposure_heatmap(filtered_roles, filtered_scores)
        st.plotly_chart(fig, use_container_width=True)

    # Tab 3: Drift Analysis
    with tab3:
        st.subheader("Exposure Drift Detection")

        quarterly_dir = str(Path("data/sample/acme_corp_quarterly"))
        drift_results = load_drift_data(quarterly_dir, reference_path)

        if drift_results is None:
            st.info(
                "Drift analysis requires multi-period data. "
                "Use `aedm drift --input-dir quarterly_snapshots/` for full analysis."
            )
        else:
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
                    pd.DataFrame(drift_table), use_container_width=True, hide_index=True
                )

            significant = [
                dr for dr in drift_results if dr.direction.value != "Stable"
            ]
            if significant:
                dept_names = ", ".join(dr.entity_id for dr in significant)
                st.warning(
                    f"{len(significant)} department(s) show significant drift: {dept_names}"
                )

            with st.expander("How Drift Detection Works"):
                st.markdown(
                    "AEDM uses **CUSUM (Cumulative Sum) changepoint detection** to identify "
                    "shifts in exposure trends over time. Statistical significance is assessed "
                    "via **permutation testing** — the observed CUSUM statistic is compared "
                    "against a null distribution of 1,000 random permutations. A **linear "
                    "trend slope** quantifies the rate of exposure change per period."
                )

    # Tab 4: Demographics
    with tab4:
        st.subheader("Demographic Disparity Analysis")
        st.info(
            "Anthropic's research found AI exposure systematically skews toward "
            "female workers, more-educated workers, and higher-paid workers — "
            "driven by the concentration of knowledge work tasks in these segments."
        )
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
                        "Flagged": "⚠️" if s.flagged else "",
                    }
                    for s in segments
                ]
            )
            st.dataframe(seg_df, use_container_width=True, hide_index=True)

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
                "**Intersectional analysis** (e.g., gender × education × pay band) "
                "is not currently supported. Single-dimension analysis may mask "
                "compounding effects."
            )
            st.markdown(
                "These findings should **inform planning conversations**, not determine "
                "individual employment outcomes."
            )

    # Tab 5: Reskilling Priority
    with tab5:
        st.subheader("Reskilling Urgency Rankings")
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
            new_blended = 0.4 * s.theoretical + 0.6 * new_observed
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


if __name__ == "__main__":
    main()
