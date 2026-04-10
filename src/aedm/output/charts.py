"""Visualization engine using Plotly and matplotlib."""

from __future__ import annotations

from io import BytesIO

import plotly.graph_objects as go
import structlog

from aedm.config import settings
from aedm.models.schemas import (
    DemographicSegment,
    DriftResult,
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
    title: str = "AI Exposure by Department and Role",
) -> go.Figure:
    """Create a department × exposure heatmap.

    Args:
        roles: List of Role objects.
        scores: Corresponding ExposureScore objects.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    score_map = {s.role_id: s for s in scores}

    # Group by department
    dept_data: dict[str, list[tuple[str, float, int]]] = {}
    for role in roles:
        score = score_map.get(role.role_id)
        if score is None:
            continue
        dept = role.department
        if dept not in dept_data:
            dept_data[dept] = []
        dept_data[dept].append((role.title, score.blended, role.headcount))

    # Sort departments by mean exposure
    dept_means = {
        dept: sum(s for _, s, _ in data) / len(data)
        for dept, data in dept_data.items()
    }
    sorted_depts = sorted(dept_means, key=lambda d: dept_means[d], reverse=True)

    fig = go.Figure()

    for dept in sorted_depts:
        entries = sorted(dept_data[dept], key=lambda x: -x[1])[:10]  # Top 10 per dept
        for role_title, blended, headcount in entries:
            fig.add_trace(go.Bar(
                name=dept,
                x=[blended],
                y=[f"{dept} | {role_title}"],
                orientation="h",
                marker_color=TIER_COLORS.get(
                    "Critical" if blended >= 0.75 else
                    "High" if blended >= 0.5 else
                    "Moderate" if blended >= 0.25 else "Low",
                    GRAY,
                ),
                hovertemplate=(
                    f"<b>{role_title}</b><br>"
                    f"Department: {dept}<br>"
                    f"Exposure: {blended:.2%}<br>"
                    f"Headcount: {headcount}<extra></extra>"
                ),
                showlegend=False,
            ))

    fig.update_layout(
        title=title,
        xaxis_title="Blended Exposure Score",
        xaxis=dict(range=[0, 1], tickformat=".0%"),
        yaxis=dict(autorange="reversed"),
        height=max(400, len(sorted_depts) * 120),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
        margin=dict(l=250),
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
        RED if d.direction.value == "Accelerating" else
        TEAL if d.direction.value == "Decelerating" else GRAY
        for d in sorted_results
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=slopes,
        y=entities,
        orientation="h",
        marker_color=colors,
        hovertemplate=[
            f"<b>{eid}</b><br>"
            f"Direction: {direction}<br>"
            f"Slope: {slope:+.4f}/period<br>"
            f"p-value: {pval:.3f}<extra></extra>"
            for eid, direction, slope, pval in zip(entities, directions, slopes, p_values)
        ],
    ))

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

    for seg_type in segment_types:
        type_segments = [s for s in segments if s.segment_type == seg_type]
        type_segments.sort(key=lambda s: s.disparity_ratio, reverse=True)

        labels = [s.segment_value for s in type_segments]
        ratios = [s.disparity_ratio for s in type_segments]
        colors = [RED if s.flagged else TEAL for s in type_segments]

        fig.add_trace(go.Bar(
            name=seg_type.replace("_", " ").title(),
            x=labels,
            y=ratios,
            marker_color=colors,
            hovertemplate=[
                f"<b>{label}</b> ({seg_type})<br>"
                f"Disparity Ratio: {ratio:.2f}x<br>"
                f"Mean Exposure: {seg.mean_exposure:.2%}<br>"
                f"Headcount: {seg.headcount}<br>"
                f"{'⚠ FLAGGED' if seg.flagged else 'Within threshold'}<extra></extra>"
                for label, ratio, seg in zip(labels, ratios, type_segments)
            ],
        ))

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

    fig.add_trace(go.Scatter(
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
    ))

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

    fig.add_trace(go.Histogram(
        x=values,
        nbinsx=20,
        marker_color=TEAL,
        marker_line=dict(width=1, color=NAVY),
        hovertemplate="Exposure: %{x:.2f}<br>Count: %{y}<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Blended Exposure Score",
        yaxis_title="Number of Roles",
        xaxis=dict(range=[0, 1]),
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12),
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
        return fig.to_image(format="png", width=width, height=height)  # type: ignore[return-value]
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
