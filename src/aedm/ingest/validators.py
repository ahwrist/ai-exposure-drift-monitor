"""Input data validation for AEDM."""

from __future__ import annotations

import re

import pandas as pd
import structlog

from aedm.exceptions import ValidationError

logger = structlog.get_logger()

REQUIRED_COLUMNS = {"title"}

OPTIONAL_COLUMNS = {
    "role_id": str,
    "soc_code": str,
    "department": str,
    "headcount": int,
    "gender_pct_female": float,
    "median_salary": int,
    "education_mode": str,
    "remote_pct": float,
}

VALID_EDUCATION_LEVELS = {"High School", "Associate", "Bachelor", "Master", "Doctorate"}

SOC_CODE_PATTERN = re.compile(r"^\d{2}-\d{4}$")


def validate_dataframe(df: pd.DataFrame) -> list[str]:
    """Validate an org data DataFrame and return a list of error messages.

    Args:
        df: Raw DataFrame from CSV/JSON ingestion.

    Returns:
        List of validation error strings. Empty list means valid.
    """
    errors: list[str] = []

    if df.empty:
        errors.append("Input data is empty — no rows found.")
        return errors

    # Check required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        errors.append(f"Missing required column(s): {', '.join(sorted(missing))}")
        return errors  # Can't proceed without required columns

    # Check for empty titles
    blank_titles = df["title"].isna() | (df["title"].astype(str).str.strip() == "")
    if blank_titles.any():
        count = int(blank_titles.sum())
        errors.append(f"{count} row(s) have blank or missing 'title' values.")

    # Validate SOC codes if present
    if "soc_code" in df.columns:
        filled = df["soc_code"].dropna()
        filled = filled[filled.astype(str).str.strip() != ""]
        bad_soc = ~filled.astype(str).apply(lambda x: bool(SOC_CODE_PATTERN.match(x)))
        if bad_soc.any():
            bad_values = filled[bad_soc].head(3).tolist()
            errors.append(
                f"{int(bad_soc.sum())} invalid SOC code(s) "
                f"(expected format XX-XXXX): {bad_values}"
            )

    # Validate headcount if present
    if "headcount" in df.columns:
        hc = pd.to_numeric(df["headcount"], errors="coerce")
        bad_hc = hc.notna() & (hc < 1)
        if bad_hc.any():
            errors.append(f"{int(bad_hc.sum())} row(s) have headcount < 1.")

    # Validate percentage fields
    for pct_col in ("gender_pct_female", "remote_pct"):
        if pct_col in df.columns:
            vals = pd.to_numeric(df[pct_col], errors="coerce")
            out_of_range = vals.notna() & ((vals < 0) | (vals > 1))
            if out_of_range.any():
                errors.append(
                    f"{int(out_of_range.sum())} row(s) have {pct_col} outside [0, 1]."
                )

    # Validate education levels if present
    if "education_mode" in df.columns:
        filled_edu = df["education_mode"].dropna()
        filled_edu = filled_edu[filled_edu.astype(str).str.strip() != ""]
        invalid_edu = ~filled_edu.isin(VALID_EDUCATION_LEVELS)
        if invalid_edu.any():
            bad_vals = filled_edu[invalid_edu].unique()[:3].tolist()
            errors.append(
                f"{int(invalid_edu.sum())} row(s) have invalid education_mode. "
                f"Expected one of {sorted(VALID_EDUCATION_LEVELS)}. Got: {bad_vals}"
            )

    # Validate salary if present
    if "median_salary" in df.columns:
        sal = pd.to_numeric(df["median_salary"], errors="coerce")
        bad_sal = sal.notna() & (sal < 0)
        if bad_sal.any():
            errors.append(f"{int(bad_sal.sum())} row(s) have negative median_salary.")

    if errors:
        logger.warning("validation_errors", count=len(errors))
    else:
        logger.info("validation_passed", rows=len(df))

    return errors


def validate_or_raise(df: pd.DataFrame) -> None:
    """Validate a DataFrame and raise ValidationError if invalid.

    Args:
        df: Raw DataFrame from CSV/JSON ingestion.

    Raises:
        ValidationError: If any validation errors are found.
    """
    errors = validate_dataframe(df)
    if errors:
        raise ValidationError(errors)
