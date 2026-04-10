"""Output layer: charts, reports, and structured export."""

from aedm.output.charts import (
    demographic_disparity_bars,
    drift_sparklines,
    exposure_distribution,
    exposure_heatmap,
    urgency_matrix,
)
from aedm.output.export import export_csv, export_json, scores_to_dataframe
from aedm.output.report import (
    generate_html_report,
    generate_markdown_report,
    save_report,
)

__all__ = [
    "demographic_disparity_bars",
    "drift_sparklines",
    "export_csv",
    "export_json",
    "exposure_distribution",
    "exposure_heatmap",
    "generate_html_report",
    "generate_markdown_report",
    "save_report",
    "scores_to_dataframe",
    "urgency_matrix",
]
