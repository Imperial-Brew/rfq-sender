import os
from pathlib import Path
import pandas as pd
import pytest

from core.specs.spec_manager import SpecManager


@pytest.fixture()
def tmp_specs_csv(tmp_path: Path) -> Path:
    # Create a minimal familiar specs CSV
    df = pd.DataFrame(
        {
            "process": ["anodize", "AnOdIzE", "paint", None],
            "spec": ["MIL-A-8625", "AMS 2469", "ISO 12944", "N/A"],
            "issuer": ["MIL", "SAE", "ISO", ""],
            "notes": ["", "", "", ""],
        }
    )
    csv_path = tmp_path / "FamiliarSpecs.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


def test_load_specs_for_process_none_returns_empty(tmp_specs_csv: Path) -> None:
    mgr = SpecManager(str(tmp_specs_csv))
    assert mgr.load_specs_for_process(None) == []


def test_load_specs_for_process_empty_returns_empty(tmp_specs_csv: Path) -> None:
    mgr = SpecManager(str(tmp_specs_csv))
    assert mgr.load_specs_for_process("") == []
    assert mgr.load_specs_for_process("   ") == []


def test_load_specs_for_process_case_insensitive(tmp_specs_csv: Path) -> None:
    mgr = SpecManager(str(tmp_specs_csv))
    specs = mgr.load_specs_for_process("ANODIZE")
    # Both anodize rows should be normalized and included
    assert set(specs) == {"AMS 2469", "MIL-A-8625"}


def test_load_specs_for_process_missing_columns_returns_empty(tmp_path: Path) -> None:
    # Create CSV missing required columns
    df = pd.DataFrame({"foo": [1, 2], "bar": [3, 4]})
    path = tmp_path / "FamiliarSpecs.csv"
    df.to_csv(path, index=False)

    mgr = SpecManager(str(path))
    assert mgr.load_specs_for_process("anything") == []
