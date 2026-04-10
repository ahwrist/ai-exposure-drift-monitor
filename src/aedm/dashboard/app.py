"""Streamlit interactive dashboard for AEDM."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure src is on path when running standalone
_src = Path(__file__).resolve().parent.parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from aedm.analysis.demographics import analyze_all_disparities
from aedm.analysis.exposure import (
    compute_org_exposure,
    exposure_by_department,
    org_mean_exposure,
)
from aedm.analysis.reskill import score_org_urgency
from aedm.config import settings
from aedm.ingest.parser import load_reference_rates, parse_csv
from aedm.models.enums import ExposureTier
from aedm.output.charts import (
    demographic_disparity_bars,
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
    input_path: str, reference_path: str,
) -> tuple:
    """Load and compute all analysis data."""
    roles = parse_csv(Path(input_path))
    rates = load_reference_rates(Path(reference_path))
    scores = compute_org_exposure(roles, rates)
    mean_exp = org_mean_exposure(roles, scores)
    dept_exp = exposure_by_department(roles, scores)
    urgency = score_org_urgency(roles, scores, None, rates)
    segments = analyze_all_disparities(roles, scores)
    return roles, rates, scores, mean_exp, dept_exp, urgency, segments


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
    urgency_map = {u.role_id: u for u in urgency}

    # Department filter
    departments = sorted(set(r.department for r in roles))
    selected_depts = st.sidebar.multiselect(
        "Filter departments", departments, default=departments
    )

    filtered_roles = [r for r in roles if r.department in selected_depts]
    filtered_scores = [s for s in scores if any(
        r.role_id == s.role_id for r in filtered_roles
    )]

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Org Overview", "Exposure Heatmap", "Drift Analysis",
        "Demographics", "Reskilling Priority", "Scenario"
    ])

    # Tab 1: Org Overview
    with tab1:
        total_hc = sum(r.headcount for r in filtered_roles)
        filtered_mean = (
            sum(score_map[r.role_id].blended * r.headcount for r in filtered_roles if r.role_id in score_map)
            / total_hc if total_hc > 0 else 0
        )

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

        st.plotly_chart(exposure_distribution(filtered_scores), use_container_width=True)

        # Top 10 most exposed roles
        st.subheader("Top 10 Most Exposed Roles")
        top_roles = sorted(filtered_scores, key=lambda s: s.blended, reverse=True)[:10]
        role_map = {r.role_id: r for r in filtered_roles}
        top_data = []
        for s in top_roles:
            r = role_map.get(s.role_id)
            if r:
                top_data.append({
                    "Title": r.title,
                    "Department": r.department,
                    "Exposure": f"{s.blended:.1%}",
                    "Tier": s.tier.value,
                    "Headcount": r.headcount,
                })
        if top_data:
            st.dataframe(pd.DataFrame(top_data), use_container_width=True, hide_index=True)

    # Tab 2: Exposure Heatmap
    with tab2:
        st.subheader("Department × Role Exposure")
        exposure_view = st.radio(
            "Exposure metric",
            ["Blended", "Theoretical", "Observed"],
            horizontal=True,
        )
        fig = exposure_heatmap(filtered_roles, filtered_scores)
        st.plotly_chart(fig, use_container_width=True)

    # Tab 3: Drift Analysis
    with tab3:
        st.subheader("Exposure Drift Detection")
        st.info(
            "Drift analysis requires multi-period data. "
            "Use `aedm drift --input-dir quarterly_snapshots/` for full analysis."
        )
        st.markdown(
            "Upload quarterly CSV files to detect changepoints and trends "
            "in AI exposure across your organization."
        )

    # Tab 4: Demographics
    with tab4:
        st.subheader("Demographic Disparity Analysis")
        if segments:
            flagged = [s for s in segments if s.flagged]
            if flagged:
                st.warning(f"{len(flagged)} segment(s) flagged for disproportionate exposure.")
            else:
                st.success("No segments exceed the disparity threshold.")

            fig = demographic_disparity_bars(segments)
            st.plotly_chart(fig, use_container_width=True)

            seg_df = pd.DataFrame([
                {
                    "Type": s.segment_type.replace("_", " ").title(),
                    "Segment": s.segment_value,
                    "Mean Exposure": f"{s.mean_exposure:.1%}",
                    "Disparity Ratio": f"{s.disparity_ratio:.2f}x",
                    "Headcount": s.headcount,
                    "Flagged": "⚠️" if s.flagged else "",
                }
                for s in segments
            ])
            st.dataframe(seg_df, use_container_width=True, hide_index=True)

    # Tab 5: Reskilling Priority
    with tab5:
        st.subheader("Reskilling Urgency Rankings")

        fig = urgency_matrix(filtered_roles, filtered_scores, urgency)
        st.plotly_chart(fig, use_container_width=True)

        urg_data = []
        for u in urgency[:30]:
            r = {r_.role_id: r_ for r_ in roles}.get(u.role_id)
            if r and r.department in selected_depts:
                urg_data.append({
                    "Title": r.title,
                    "Department": r.department,
                    "Urgency Score": f"{u.score:.1%}",
                    "Tier": u.tier.value,
                    "Headcount": r.headcount,
                })
        if urg_data:
            st.dataframe(pd.DataFrame(urg_data), use_container_width=True, hide_index=True)

    # Tab 6: Scenario Modeling
    with tab6:
        st.subheader("What-If Scenario: Exposure Acceleration")
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
            scenario_scores.append({
                "role_id": s.role_id,
                "current_blended": s.blended,
                "scenario_blended": new_blended,
                "change": new_blended - s.blended,
                "current_tier": s.tier.value,
                "scenario_tier": new_tier.value,
            })

        scenario_df = pd.DataFrame(scenario_scores)
        role_lookup = {r.role_id: r for r in roles}

        # Summary metrics
        current_mean = scenario_df["current_blended"].mean()
        scenario_mean = scenario_df["scenario_blended"].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Current Mean Exposure", f"{current_mean:.1%}")
        col2.metric("Scenario Mean Exposure", f"{scenario_mean:.1%}", f"+{scenario_mean - current_mean:.1%}")

        current_critical = (scenario_df["current_tier"] == "Critical").sum()
        scenario_critical = (scenario_df["scenario_tier"] == "Critical").sum()
        col3.metric("Critical-Tier Roles", scenario_critical, f"+{scenario_critical - current_critical}")

        # Show biggest movers
        scenario_df["title"] = scenario_df["role_id"].map(lambda x: role_lookup.get(x, None))
        scenario_df["title"] = scenario_df["title"].apply(lambda r: r.title if r else "")
        scenario_df = scenario_df.sort_values("change", ascending=False)

        st.subheader("Biggest Impact Roles")
        display_df = scenario_df.head(15)[["title", "current_blended", "scenario_blended", "change", "scenario_tier"]]
        display_df.columns = ["Title", "Current", "Scenario", "Change", "New Tier"]
        display_df["Current"] = display_df["Current"].apply(lambda x: f"{x:.1%}")
        display_df["Scenario"] = display_df["Scenario"].apply(lambda x: f"{x:.1%}")
        display_df["Change"] = display_df["Change"].apply(lambda x: f"+{x:.1%}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
