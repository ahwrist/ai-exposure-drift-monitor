"""Visualization engine using Plotly and matplotlib."""

from __future__ import annotations

from io import BytesIO

import plotly.graph_objects as go
import structlog

from aedm.config import settings
from aedm.models.schemas import (
    DemographicSegment,
    DriftResult,
    ExposureRate,
    ExposureScore,
    Role,
    UrgencyScore,
)

logger = structlog.get_logger()

# Color palette
NAVY = settings.color_navy
TEAL = settings.color_teal
AMBER = settings.color_amber
GRAY = settings.color_gray
RED = settings.color_red

TIER_COLORS = {
    "Critical": RED,
    "High": AMBER,
    "Moderate": TEAL,
    "Low": GRAY,
}


def exposure_heatmap(
    roles: list[Role],
    scores: list[ExposureScore],
    metric: str = "blended",
    title: str = "AI Exposure by Department — Role Count per Tier",
) -> go.Figure:
    """Create a department × exposure-tier headcount heatmap.

    Each cell shows how many roles in a department fall into a given
    exposure tier (Critical/High/Moderate/Low).  Hover reveals the
    specific role titles in that cell.

    Args:
        roles: List of Role objects.
        scores: Corresponding ExposureScore objects.
        metric: Which score to use for tier assignment —
                "blended", "theoretical", or "observed".
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    tier_labels = [
        "Critical (\u226575%)",
        "High (50-74%)",
        "Moderate (25-49%)",
        "Low (<25%)",
    ]

    def _tier_index(value: float) -> int:
        if value >= 0.75:
            return 0
        if value >= 0.50:
            return 1
        if value >= 0.25:
            return 2
        return 3

    score_map = {s.role_id: s for s in scores}

    # Group roles by department → tier
    dept_tier_roles: dict[str, list[list[str]]] = {}
    dept_score_sums: dict[str, tuple[float, int]] = {}
    for role in roles:
        score = score_map.get(role.role_id)
        if score is None:
            continue
        dept = role.department
        score_value: float = getattr(score, metric, score.blended)
        if dept not in dept_tier_roles:
            dept_tier_roles[dept] = [[] for _ in tier_labels]
            dept_score_sums[dept] = (0.0, 0)
        dept_tier_roles[dept][_tier_index(score_value)].append(role.title)
        total, count = dept_score_sums[dept]
        dept_score_sums[dept] = (total + score_value, count + 1)

    # Sort departments by mean exposure descending
    sorted_depts = sorted(
        dept_tier_roles,
        key=lambda d: dept_score_sums[d][0] / dept_score_sums[d][1],
        reverse=True,
    )

    # Build z (counts) and hover text matrices
    z_values: list[list[int]] = []
    hover_texts: list[list[str]] = []
    for dept in sorted_depts:
        z_row: list[int] = []
        hover_row: list[str] = []
        for tier_idx, tier_label in enumerate(tier_labels):
            role_titles = dept_tier_roles[dept][tier_idx]
            count = len(role_titles)
            z_row.append(count)
            roles_list = ", ".join(sorted(role_titles)) if role_titles else "(none)"
            hover_row.append(
                f"<b>{dept}</b><br>"
                f"Tier: {tier_label}<br>"
                f"Roles: {count}<br>"
                f"Titles: {roles_list}"
            )
        z_values.append(z_row)
        hover_texts.append(hover_row)

    fig = go.Figure()

    fig.add_trace(
        go.Heatmap(
            z=z_values,
            x=tier_labels,
            y=sorted_depts,
            hovertext=hover_texts,
            hovertemplate="%{hovertext}<extra></extra>",
            texttemplate="%{z}",
            colorscale=[
                [0.0, "#F0F0F0"],
                [1.0, "#1B2A4A"],
            ],
            zmin=0,
            colorbar=dict(title="Role Count"),
            xgap=3,
            ygap=3,
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Exposure Tier",
        yaxis_title="Department",
        height=max(400, len(sorted_depts) * 60 + 200),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
    )

    return fig


def drift_sparklines(
    drift_results: list[DriftResult],
    title: str = "Exposure Drift by Entity",
) -> go.Figure:
    """Create sparkline-style drift summary chart.

    Args:
        drift_results: List of DriftResult objects.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    # Sort by magnitude
    sorted_results = sorted(drift_results, key=lambda d: d.magnitude, reverse=True)

    entities = [d.entity_id for d in sorted_results]
    slopes = [d.trend_slope for d in sorted_results]
    p_values = [d.p_value for d in sorted_results]
    directions = [d.direction.value for d in sorted_results]

    colors = [
        RED
        if d.direction.value == "Accelerating"
        else TEAL
        if d.direction.value == "Decelerating"
        else GRAY
        for d in sorted_results
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=slopes,
            y=entities,
            orientation="h",
            marker_color=colors,
            hovertemplate=[
                f"<b>{eid}</b><br>"
                f"Direction: {direction}<br>"
                f"Slope: {slope:+.4f}/period<br>"
                f"p-value: {pval:.3f}<extra></extra>"
                for eid, direction, slope, pval in zip(
                    entities, directions, slopes, p_values, strict=True
                )
            ],
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Trend Slope (exposure change per period)",
        yaxis=dict(autorange="reversed"),
        height=max(400, len(entities) * 30),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
    )

    return fig


def demographic_disparity_bars(
    segments: list[DemographicSegment],
    title: str = "Exposure Disparity by Demographic Segment",
) -> go.Figure:
    """Create a grouped bar chart of demographic disparity ratios.

    Args:
        segments: List of DemographicSegment objects.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure()

    segment_types = sorted(set(s.segment_type for s in segments))

    # Distinct base color per segment type
    segment_base_colors: dict[str, str] = {
        "gender": TEAL,
        "education": AMBER,
        "pay_band": NAVY,
    }

    for seg_type in segment_types:
        type_segments = [s for s in segments if s.segment_type == seg_type]
        type_segments.sort(key=lambda s: s.disparity_ratio, reverse=True)

        base_color = segment_base_colors.get(seg_type, GRAY)
        pretty_name = seg_type.replace("_", " ").title()

        # Split into flagged / unflagged groups for distinct legend entries
        flagged = [s for s in type_segments if s.flagged]
        unflagged = [s for s in type_segments if not s.flagged]

        for group, color, suffix in [
            (unflagged, base_color, ""),
            (flagged, RED, " (flagged)"),
        ]:
            if not group:
                continue
            labels = [s.segment_value for s in group]
            ratios = [s.disparity_ratio for s in group]
            fig.add_trace(
                go.Bar(
                    name=f"{pretty_name}{suffix}",
                    x=labels,
                    y=ratios,
                    marker_color=color,
                    legendgroup=seg_type,
                    hovertemplate=[
                        f"<b>{s.segment_value}</b> ({seg_type})<br>"
                        f"Disparity Ratio: {s.disparity_ratio:.2f}x<br>"
                        f"Mean Exposure: {s.mean_exposure:.2%}<br>"
                        f"Headcount: {s.headcount}<br>"
                        f"{'⚠ FLAGGED' if s.flagged else 'Within threshold'}"
                        "<extra></extra>"
                        for s in group
                    ],
                )
            )

    # Add threshold line
    fig.add_hline(
        y=settings.disparity_flag_threshold,
        line_dash="dash",
        line_color=RED,
        annotation_text=f"Flag threshold ({settings.disparity_flag_threshold}x)",
    )
    fig.add_hline(y=1.0, line_dash="dot", line_color=NAVY, annotation_text="Org mean")

    fig.update_layout(
        title=title,
        yaxis_title="Disparity Ratio (segment / org mean)",
        barmode="group",
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
    )

    return fig


def urgency_matrix(
    roles: list[Role],
    scores: list[ExposureScore],
    urgency_scores: list[UrgencyScore],
    title: str = "Reskilling Urgency Matrix",
) -> go.Figure:
    """Create an urgency scatter matrix (exposure × urgency, sized by headcount).

    Args:
        roles: List of Role objects.
        scores: Corresponding ExposureScore objects.
        urgency_scores: UrgencyScore objects.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    role_map = {r.role_id: r for r in roles}
    score_map = {s.role_id: s for s in scores}

    x_vals = []
    y_vals = []
    sizes = []
    labels = []
    colors = []
    hover_texts = []

    for urgency in urgency_scores:
        role = role_map.get(urgency.role_id)
        exposure = score_map.get(urgency.role_id)
        if role is None or exposure is None:
            continue

        x_vals.append(exposure.blended)
        y_vals.append(urgency.score)
        sizes.append(max(5, role.headcount * 2))
        labels.append(role.title)
        colors.append(TIER_COLORS.get(urgency.tier.value, GRAY))
        hover_texts.append(
            f"<b>{role.title}</b><br>"
            f"Department: {role.department}<br>"
            f"Exposure: {exposure.blended:.2%}<br>"
            f"Urgency: {urgency.score:.2%} ({urgency.tier.value})<br>"
            f"Headcount: {role.headcount}"
        )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="markers",
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.7,
                line=dict(width=1, color=NAVY),
            ),
            hovertemplate=[f"{ht}<extra></extra>" for ht in hover_texts],
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Blended Exposure Score",
        yaxis_title="Reskilling Urgency Score",
        xaxis=dict(range=[0, 1], tickformat=".0%"),
        yaxis=dict(range=[0, 1], tickformat=".0%"),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        showlegend=False,
    )

    return fig


def exposure_distribution(
    scores: list[ExposureScore],
    title: str = "Exposure Score Distribution",
) -> go.Figure:
    """Create a histogram of exposure scores.

    Args:
        scores: List of ExposureScore objects.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    values = [s.blended for s in scores]

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=values,
            nbinsx=20,
            marker_color=TEAL,
            marker_line=dict(width=1, color=NAVY),
            hovertemplate="Exposure: %{x:.2f}<br>Count: %{y}<extra></extra>",
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Blended Exposure Score",
        yaxis_title="Number of Roles",
        xaxis=dict(range=[0, 1]),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
    )

    return fig


def coverage_gap_chart(
    reference_rates: dict[str, ExposureRate],
) -> go.Figure:
    """Create a horizontal grouped bar chart of theoretical vs. observed exposure.

    Args:
        reference_rates: SOC code → ExposureRate mapping.

    Returns:
        Plotly Figure showing the AI adoption gap by occupation.
    """
    # Sort ascending so highest theoretical appears at top in horizontal bar chart
    sorted_items = sorted(
        reference_rates.items(),
        key=lambda kv: kv[1].theoretical_exposure,
    )

    groups = [v.group_name for _, v in sorted_items]
    theoretical = [v.theoretical_exposure for _, v in sorted_items]
    observed = [v.observed_exposure for _, v in sorted_items]
    gaps = [v.coverage_gap for _, v in sorted_items]

    mean_gap = sum(gaps) / len(gaps) if gaps else 0

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=groups,
            x=theoretical,
            name="Theoretical Exposure",
            orientation="h",
            marker_color=NAVY,
            hovertemplate="%{y}<br>Theoretical: %{x:.1%}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=groups,
            x=observed,
            name="Observed Exposure",
            orientation="h",
            marker_color=TEAL,
            hovertemplate="%{y}<br>Observed: %{x:.1%}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=groups,
            x=gaps,
            name="Coverage Gap",
            orientation="h",
            marker_color=AMBER,
            opacity=0.6,
            hovertemplate="%{y}<br>Gap: %{x:.1%}<extra></extra>",
        )
    )

    # Mean gap vertical line
    fig.add_vline(
        x=mean_gap,
        line_dash="dash",
        line_color=RED,
        annotation_text=f"Mean gap: {mean_gap:.1%}",
        annotation_position="top right",
    )

    fig.update_layout(
        title=dict(
            text="The AI Adoption Gap: Theoretical vs. Observed Exposure by Occupation",
            font=dict(size=18),
        ),
        barmode="group",
        xaxis_title="Exposure Rate",
        xaxis=dict(tickformat=".0%", range=[0, 1]),
        yaxis_title="",
        height=750,
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=320, t=100),
        annotations=[
            dict(
                text="Source: Massenkoff & McCrory (2026), Anthropic Economic Index",
                xref="paper",
                yref="paper",
                x=0,
                y=1.06,
                showarrow=False,
                font=dict(size=11, color="gray"),
            ),
        ],
    )

    return fig


def figure_to_png(fig: go.Figure, width: int = 1200, height: int = 600) -> bytes:
    """Export a Plotly figure to PNG bytes using matplotlib fallback.

    Args:
        fig: Plotly Figure object.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        PNG image as bytes.
    """
    try:
        return bytes(fig.to_image(format="png", width=width, height=height))
    except (ValueError, ImportError):
        # Fallback: save as HTML string indicator
        logger.warning("png_export_fallback", reason="kaleido not installed")
        import matplotlib.pyplot as plt

        buf = BytesIO()
        plt_fig, ax = plt.subplots(figsize=(width / 100, height / 100))
        ax.text(0.5, 0.5, "Install kaleido for PNG export", ha="center", va="center")
        plt_fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(plt_fig)
        buf.seek(0)
        return buf.read()
