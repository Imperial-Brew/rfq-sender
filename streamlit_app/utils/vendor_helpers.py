from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Parent dir = project root
parent_dir = Path(__file__).parent.parent.parent

# External deps used by helpers
from scripts.utils.spec_check import SpecProcessValidator


def normalize_process_spec(text: str, validator: Optional[SpecProcessValidator] = None) -> str:
    """
    Normalize a process or spec name using the SpecProcessValidator.

    Args:
        text: The process or spec name to normalize
        validator: Optional SpecProcessValidator instance. If None, a new one will be created.

    Returns:
        The normalized process or spec name
    """
    if not text:
        return ""

    if validator is None:
        validator = SpecProcessValidator()

    return validator.normalize(text)


def build_familiarity_report(queue: pd.DataFrame) -> pd.DataFrame:
    """
    Build a report for rows whose process/spec are not in familiar list.
    Preference order for familiarity source:
    1) familiar_specs.csv (if present) under docs/OS/spec_lists/ or docs/
    2) vendor_options.yaml via SpecProcessValidator (fallback)
    """
    # Try to load familiar_specs.csv if available
    csv_paths = [
        os.path.join(parent_dir, 'docs', 'OS', 'spec_lists', 'familiar_specs.csv'),
        os.path.join(parent_dir, 'docs', 'familiar_specs.csv'),
    ]
    familiar_processes: set[str] = set()
    familiar_specs: set[str] = set()
    used_csv = None
    for p in csv_paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(p, encoding='cp1252')
            used_csv = p
            # Normalize column names
            lower_cols = {c.lower(): c for c in df.columns}
            if 'process' in lower_cols:
                col = lower_cols['process']
                familiar_processes = {SpecProcessValidator.normalize(str(x)) for x in df[col].dropna().astype(str)}
            if 'spec' in lower_cols:
                col = lower_cols['spec']
                familiar_specs = {SpecProcessValidator.normalize(str(x)) for x in df[col].dropna().astype(str)}
            break
    use_validator = False
    validator = None
    if not used_csv:
        # Fallback to validator (vendor_options.yaml)
        validator = SpecProcessValidator()
        use_validator = True

    rows = []
    for idx, row in queue.iterrows():
        proc = str(row.get('process', '') or '')
        spec = str(row.get('spec', '') or '')
        if use_validator:
            proc_ok, proc_norm, proc_suggestions = validator.check_process(proc)
            spec_ok, spec_norm, spec_suggestions = validator.check_spec(spec)
        else:
            # CSV-based check: membership on normalized tokens
            proc_norm = SpecProcessValidator.normalize(proc)
            spec_norm = SpecProcessValidator.normalize(spec)
            proc_ok = (proc_norm in familiar_processes) if familiar_processes else True
            spec_ok = (spec_norm in familiar_specs) if familiar_specs else True
            proc_suggestions = []
            spec_suggestions = []
        if not proc_ok or not spec_ok:
            rows.append({
                'row_index': idx,
                'part_number': row.get('part_number', ''),
                'process': proc,
                'process_normalized': proc_norm,
                'process_ok': proc_ok,
                'process_suggestions': "; ".join(proc_suggestions) if proc_suggestions else '',
                'spec': spec,
                'spec_normalized': spec_norm,
                'spec_ok': spec_ok,
                'spec_suggestions': "; ".join(spec_suggestions) if spec_suggestions else '',
                'source': used_csv or 'vendor_options.yaml',
            })
    return pd.DataFrame(rows)


def find_vendors_for_process_spec(
    vendor_info: Dict[str, Dict[str, Any]],
    process: str,
    spec: Optional[str] = None,
    validator: Optional[SpecProcessValidator] = None,
) -> List[Dict[str, Any]]:
    """
    Find vendors that can handle a specific process and optionally a spec.

    Args:
        vendor_info: Dictionary mapping vendor_id to vendor information
        process: Process name to match
        spec: Optional spec name to match
        validator: Optional SpecProcessValidator instance

    Returns:
        List of vendor dictionaries that can handle the process/spec
    """
    if validator is None:
        validator = SpecProcessValidator()

    # Normalize process and spec for comparison
    normalized_process = normalize_process_spec(process, validator)
    normalized_spec = normalize_process_spec(spec, validator) if spec else None

    matching_vendors: List[Dict[str, Any]] = []
    process_only_vendors: List[Dict[str, Any]] = []

    for vendor_id, vendor_data in vendor_info.items():
        if 'processes' not in vendor_data:
            continue

        can_handle_process = False
        can_handle_spec = normalized_spec is None  # If no spec is provided, default to True

        for vendor_process in vendor_data['processes']:
            if not vendor_process or 'name' not in vendor_process:
                continue
            vendor_process_name = normalize_process_spec(vendor_process['name'], validator)
            if vendor_process_name == normalized_process:
                can_handle_process = True
                # If spec is provided, check if vendor can handle it
                if normalized_spec and 'specs' in vendor_process and vendor_process['specs']:
                    for vendor_spec in vendor_process['specs']:
                        if not vendor_spec:
                            continue
                        if isinstance(vendor_spec, dict):
                            raw_spec = vendor_spec.get('number') or vendor_spec.get('name') or ''
                        else:
                            raw_spec = vendor_spec
                        vendor_spec_name = normalize_process_spec(raw_spec, validator)
                        if vendor_spec_name == normalized_spec:
                            can_handle_spec = True
                            break
                # If we found a match for both process and spec (or no spec was required), stop checking
                if can_handle_process and can_handle_spec:
                    break

        if can_handle_process and can_handle_spec:
            vendor_copy = vendor_data.copy()
            vendor_copy['id'] = vendor_id
            matching_vendors.append(vendor_copy)
        elif can_handle_process and normalized_spec is not None:
            # remember for fallback when spec provided but no matches
            vendor_copy = vendor_data.copy()
            vendor_copy['id'] = vendor_id
            process_only_vendors.append(vendor_copy)

    # Fallback: if spec given but no exact spec matches, return process-only vendors
    if normalized_spec is not None and not matching_vendors and process_only_vendors:
        return process_only_vendors

    return matching_vendors
