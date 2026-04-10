"""Tests for the ingestion layer: validation, parsing, and SOC mapping."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aedm.exceptions import ValidationError
from aedm.ingest.onet_mapper import map_roles, map_title_to_soc
from aedm.ingest.parser import load_reference_rates, parse_csv
from aedm.ingest.validators import validate_dataframe


class TestValidation:
    """Tests for input data validation."""

    def test_valid_dataframe_passes(self) -> None:
        df = pd.DataFrame({
            "title": ["Software Engineer", "Data Analyst"],
            "headcount": [10, 5],
        })
        errors = validate_dataframe(df)
        assert errors == []

    def test_missing_title_column_fails(self) -> None:
        df = pd.DataFrame({"headcount": [10]})
        errors = validate_dataframe(df)
        assert any("title" in e for e in errors)

    def test_empty_dataframe_fails(self) -> None:
        df = pd.DataFrame()
        errors = validate_dataframe(df)
        assert any("empty" in e.lower() for e in errors)

    def test_invalid_soc_code_flagged(self) -> None:
        df = pd.DataFrame({
            "title": ["Test Role"],
            "soc_code": ["INVALID"],
        })
        errors = validate_dataframe(df)
        assert any("SOC" in e for e in errors)

    def test_valid_soc_code_passes(self) -> None:
        df = pd.DataFrame({
            "title": ["Test Role"],
            "soc_code": ["15-1252"],
        })
        errors = validate_dataframe(df)
        assert errors == []

    def test_negative_headcount_flagged(self) -> None:
        df = pd.DataFrame({
            "title": ["Test Role"],
            "headcount": [-1],
        })
        errors = validate_dataframe(df)
        assert any("headcount" in e for e in errors)

    def test_percentage_out_of_range_flagged(self) -> None:
        df = pd.DataFrame({
            "title": ["Test Role"],
            "gender_pct_female": [1.5],
        })
        errors = validate_dataframe(df)
        assert any("gender_pct_female" in e for e in errors)

    def test_invalid_education_flagged(self) -> None:
        df = pd.DataFrame({
            "title": ["Test Role"],
            "education_mode": ["PhD"],  # Should be "Doctorate"
        })
        errors = validate_dataframe(df)
        assert any("education_mode" in e for e in errors)

    def test_blank_title_flagged(self) -> None:
        df = pd.DataFrame({
            "title": ["", "Valid Title"],
        })
        errors = validate_dataframe(df)
        assert any("blank" in e.lower() for e in errors)


class TestParser:
    """Tests for CSV/JSON parsing."""

    def test_parse_sample_csv(self, sample_csv_path: Path) -> None:
        roles = parse_csv(sample_csv_path)
        assert len(roles) == 200
        assert all(r.role_id for r in roles)
        assert all(r.title for r in roles)

    def test_parse_csv_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            parse_csv(Path("nonexistent.csv"))

    def test_parse_csv_assigns_soc_codes(self, sample_csv_path: Path) -> None:
        roles = parse_csv(sample_csv_path)
        # All sample roles have SOC codes in the CSV
        assert all(r.soc_code for r in roles)

    def test_load_reference_rates(self, reference_path: Path) -> None:
        rates = load_reference_rates(reference_path)
        assert len(rates) == 22
        assert "15-0000" in rates
        assert rates["15-0000"].theoretical_exposure == 0.94

    def test_role_soc_major_group(self) -> None:
        from aedm.models.schemas import Role
        role = Role(role_id="X", title="Test", soc_code="15-1252")
        assert role.soc_major_group == "15-0000"


class TestOnetMapper:
    """Tests for SOC code mapping."""

    def test_exact_match(self) -> None:
        soc, confidence = map_title_to_soc("Software Engineer")
        assert soc == "15-1252"
        assert confidence == 100

    def test_exact_match_case_insensitive(self) -> None:
        soc, _ = map_title_to_soc("software engineer")
        assert soc == "15-1252"

    def test_fuzzy_match(self) -> None:
        soc, confidence = map_title_to_soc("Sr. Software Engineer")
        assert soc == "15-1252"
        assert confidence >= 80

    def test_no_match_returns_empty(self) -> None:
        soc, confidence = map_title_to_soc("Quantum Entanglement Specialist", threshold=99)
        assert soc == ""

    def test_map_roles_preserves_existing_soc(self) -> None:
        from aedm.models.schemas import Role
        roles = [Role(role_id="X", title="Test", soc_code="15-1252")]
        mapped = map_roles(roles)
        assert mapped[0].soc_code == "15-1252"

    def test_map_roles_fills_missing_soc(self) -> None:
        from aedm.models.schemas import Role
        roles = [Role(role_id="X", title="Financial Analyst")]
        mapped = map_roles(roles)
        assert mapped[0].soc_code == "13-2051"

    def test_map_roles_with_sample_data(self, sample_csv_path: Path) -> None:
        roles = parse_csv(sample_csv_path)
        mapped = map_roles(roles)
        assert len(mapped) == len(roles)
