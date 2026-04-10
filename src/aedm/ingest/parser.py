"""CSV/JSON ingestion with validation for AEDM."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import structlog

from aedm.exceptions import ReferenceDataError, ValidationError
from aedm.ingest.validators import validate_or_raise
from aedm.models.schemas import ExposureRate, OrgSnapshot, Role

logger = structlog.get_logger()


def _assign_role_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Add auto-generated role_id column if missing."""
    if "role_id" not in df.columns or df["role_id"].isna().all():
        df = df.copy()
        df["role_id"] = [f"R{i + 1:03d}" for i in range(len(df))]
    return df


def _df_to_roles(df: pd.DataFrame) -> list[Role]:
    """Convert a validated DataFrame to a list of Role objects."""
    roles: list[Role] = []
    for _, row in df.iterrows():
        role_data: dict[str, object] = {
            "role_id": str(row.get("role_id", "")),
            "title": str(row["title"]).strip(),
        }
        if "soc_code" in row and pd.notna(row["soc_code"]):
            role_data["soc_code"] = str(row["soc_code"]).strip()
        if "department" in row and pd.notna(row["department"]):
            role_data["department"] = str(row["department"]).strip()
        if "headcount" in row and pd.notna(row["headcount"]):
            role_data["headcount"] = int(row["headcount"])
        if "gender_pct_female" in row and pd.notna(row["gender_pct_female"]):
            role_data["gender_pct_female"] = float(row["gender_pct_female"])
        if "median_salary" in row and pd.notna(row["median_salary"]):
            role_data["median_salary"] = int(row["median_salary"])
        if "education_mode" in row and pd.notna(row["education_mode"]):
            role_data["education_mode"] = str(row["education_mode"]).strip()
        if "remote_pct" in row and pd.notna(row["remote_pct"]):
            role_data["remote_pct"] = float(row["remote_pct"])

        roles.append(Role(**role_data))
    return roles


def parse_csv(path: Path) -> list[Role]:
    """Parse a CSV file into validated Role objects.

    Args:
        path: Path to the CSV file.

    Returns:
        List of validated Role objects.

    Raises:
        ValidationError: If the data fails validation.
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    logger.info("parsing_csv", path=str(path))
    df = pd.read_csv(path)
    df = _assign_role_ids(df)
    validate_or_raise(df)
    roles = _df_to_roles(df)
    logger.info("parsed_roles", count=len(roles))
    return roles


def parse_json_roles(path: Path) -> list[Role]:
    """Parse a JSON file containing a list of role objects.

    Args:
        path: Path to the JSON file.

    Returns:
        List of validated Role objects.

    Raises:
        ValidationError: If the data fails validation.
    """
    if not path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    logger.info("parsing_json", path=str(path))
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        df = pd.DataFrame(data)
    elif isinstance(data, dict) and "roles" in data:
        df = pd.DataFrame(data["roles"])
    else:
        raise ValidationError(['JSON must be a list of role objects or {"roles": [...]}'])

    df = _assign_role_ids(df)
    validate_or_raise(df)
    return _df_to_roles(df)


def load_quarterly_snapshots(directory: Path) -> list[OrgSnapshot]:
    """Load multiple CSV files from a directory as temporal snapshots.

    Files are sorted lexicographically to determine temporal order.

    Args:
        directory: Path to directory containing quarterly CSV files.

    Returns:
        List of OrgSnapshot objects in chronological order.

    Raises:
        FileNotFoundError: If directory does not exist.
        ValidationError: If any CSV fails validation.
    """
    if not directory.exists():
        msg = f"Directory not found: {directory}"
        raise FileNotFoundError(msg)

    csv_files = sorted(directory.glob("*.csv"))
    if not csv_files:
        raise ValidationError([f"No CSV files found in {directory}"])

    logger.info("loading_snapshots", directory=str(directory), file_count=len(csv_files))

    from datetime import datetime

    snapshots: list[OrgSnapshot] = []
    for i, csv_path in enumerate(csv_files):
        roles = parse_csv(csv_path)
        snapshot = OrgSnapshot(
            snapshot_id=f"S{i + 1:03d}",
            period_label=csv_path.stem,
            timestamp=datetime.now(),
            roles=roles,
        )
        snapshots.append(snapshot)

    logger.info("loaded_snapshots", count=len(snapshots))
    return snapshots


def load_reference_rates(path: Path) -> dict[str, ExposureRate]:
    """Load Anthropic exposure reference rates from JSON.

    Args:
        path: Path to the reference rates JSON file.

    Returns:
        Dict mapping SOC major group code to ExposureRate.

    Raises:
        ReferenceDataError: If the file is missing or malformed.
    """
    if not path.exists():
        raise ReferenceDataError(f"Reference rates file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    if "rates" not in data:
        raise ReferenceDataError("Expected 'rates' key in reference data JSON.")

    rates: dict[str, ExposureRate] = {}
    for soc_code, rate_data in data["rates"].items():
        rates[soc_code] = ExposureRate(**rate_data)

    logger.info("loaded_reference_rates", count=len(rates))
    return rates
