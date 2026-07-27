"""
bootstrap_vendor_master.py

Builds config/vendor_master.json from:
  - docs/OS/vendor_approvals_raw.csv   (output of vendor_approvals_query.sql)
  - config/process_master.json         (spec -> FPRO_ID mapping)
  - config/vendors.json                (vendor names / contact info)

Run after exporting vendor_approvals_query.sql results from SSMS:
  python scripts/bootstrap_vendor_master.py

Output: config/vendor_master.json
"""

import json
import csv
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).parent.parent

APPROVALS_CSV   = ROOT / "docs" / "OS" / "vendor_approvals_raw.csv"
PROCESS_MASTER  = ROOT / "config" / "process_master.json"
VENDORS_JSON    = ROOT / "config" / "vendors.json"
OUT             = ROOT / "config" / "vendor_master.json"


def load_process_master():
    with open(PROCESS_MASTER, encoding="utf-8") as f:
        pm = json.load(f)

    # Build reverse map: fpro_id -> list of {spec, process}
    fpro_to_specs: dict[str, list[dict]] = defaultdict(list)
    for entry in pm["specs"]:
        for fid in entry.get("fpro_ids", []):
            if fid != "SUBMISC":
                fpro_to_specs[fid].append({
                    "spec": entry["spec"],
                    "process": entry["process"],
                    "issuer": entry["issuer"],
                })
        for fid in entry.get("legacy_fpro_ids", []):
            fpro_to_specs[fid].append({
                "spec": entry["spec"],
                "process": entry["process"],
                "issuer": entry["issuer"],
                "via_legacy": True,
            })
    return fpro_to_specs


def load_vendor_names():
    with open(VENDORS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    # fvendno -> name
    return {v.get("id", "").strip(): v.get("name", "").strip()
            for v in data.get("vendors", [])}


def load_approvals(fpro_to_specs, vendor_names):
    # vendor_id -> {spec -> {fpro_id, job_count, last_used}}
    vendor_approvals: dict[str, dict] = defaultdict(dict)
    vendor_job_counts: dict[str, int] = defaultdict(int)

    with open(APPROVALS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fpro_id   = row["fpro_id"].strip()
            fvendno   = row["fvendno"].strip()
            job_count = int(row.get("job_count", 0))
            last_used = row.get("last_used", "").strip()

            specs = fpro_to_specs.get(fpro_id, [])
            if not specs:
                continue

            for spec_entry in specs:
                spec = spec_entry["spec"]
                existing = vendor_approvals[fvendno].get(spec)
                # Keep the entry with higher job_count if seen via multiple FPRO_IDs
                if existing is None or job_count > existing["job_count"]:
                    vendor_approvals[fvendno][spec] = {
                        "process":   spec_entry["process"],
                        "issuer":    spec_entry["issuer"],
                        "fpro_id":   fpro_id,
                        "job_count": job_count,
                        "last_used": last_used,
                        "via_legacy": spec_entry.get("via_legacy", False),
                    }

            vendor_job_counts[fvendno] += job_count

    return vendor_approvals, vendor_job_counts


def build_output(vendor_approvals, vendor_job_counts, vendor_names):
    vendors = []
    for fvendno, approvals in sorted(vendor_approvals.items()):
        # Group approved specs by process for readability
        by_process: dict[str, list] = defaultdict(list)
        for spec, detail in sorted(approvals.items(), key=lambda x: x[0]):
            by_process[detail["process"]].append({
                "spec":      spec,
                "issuer":    detail["issuer"],
                "fpro_id":   detail["fpro_id"],
                "job_count": detail["job_count"],
                "last_used": detail["last_used"],
                **({"via_legacy": True} if detail.get("via_legacy") else {}),
            })

        vendors.append({
            "fvendno":      fvendno,
            "name":         vendor_names.get(fvendno, ""),
            "total_jobs":   vendor_job_counts[fvendno],
            "processes":    dict(sorted(by_process.items())),
        })

    # Sort by total job volume descending
    vendors.sort(key=lambda v: v["total_jobs"], reverse=True)

    return {
        "_meta": {
            "generated":      datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_query":   "docs/OS/vendor_approvals_query.sql",
            "source_master":  "config/process_master.json",
            "vendor_count":   len(vendors),
            "note": "Approved = vendor has PO history for the FPRO_ID mapped to that spec. "
                    "via_legacy=true entries come from duplicate M2M workcenter entries (see process_master legacy_fpro_ids).",
        },
        "vendors": vendors,
    }


def main():
    if not APPROVALS_CSV.exists():
        print(f"ERROR: {APPROVALS_CSV} not found.")
        print("Run vendor_approvals_query.sql in SSMS and export results as CSV first.")
        sys.exit(1)

    print("Loading process_master.json...")
    fpro_to_specs = load_process_master()
    print(f"  {len(fpro_to_specs)} FPRO_IDs mapped")

    print("Loading vendors.json...")
    vendor_names = load_vendor_names()
    print(f"  {len(vendor_names)} vendors")

    print("Loading vendor_approvals_raw.csv...")
    vendor_approvals, vendor_job_counts = load_approvals(fpro_to_specs, vendor_names)
    print(f"  {len(vendor_approvals)} vendors with approval history")

    out = build_output(vendor_approvals, vendor_job_counts, vendor_names)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {OUT}")
    print(f"  {out['_meta']['vendor_count']} vendors")


if __name__ == "__main__":
    main()
