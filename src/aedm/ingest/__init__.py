"""Data ingestion, validation, and SOC mapping."""

from aedm.ingest.onet_mapper import map_roles, map_title_to_soc
from aedm.ingest.parser import (
    load_quarterly_snapshots,
    load_reference_rates,
    parse_csv,
    parse_json_roles,
)
from aedm.ingest.validators import validate_dataframe, validate_or_raise

__all__ = [
    "load_quarterly_snapshots",
    "load_reference_rates",
    "map_roles",
    "map_title_to_soc",
    "parse_csv",
    "parse_json_roles",
    "validate_dataframe",
    "validate_or_raise",
]
