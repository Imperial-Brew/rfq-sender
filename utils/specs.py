import pandas as pd
import os
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent
SPECS_PATH = os.path.join(ROOT_DIR, "docs", "OS", "spec_lists", "FamiliarSpecs.csv")

def load_familiar_specs():
    if not os.path.exists(SPECS_PATH):
        return pd.DataFrame(columns=["process", "spec", "issuer", "notes"])
    df = pd.read_csv(SPECS_PATH)
    df.columns = df.columns.str.strip().str.lower()  # Normalize headers
    return df

def load_process_list():
    df = load_familiar_specs()
    return df["process"].dropna().unique().tolist()

def load_specs_for_process(process):
    df = load_familiar_specs()
    if "process" not in df.columns or "spec" not in df.columns:
        return []

    # Normalize casing and spacing for matching
    df["process"] = df["process"].astype(str).str.strip().str.lower()
    df["spec"] = df["spec"].astype(str).str.strip()

    filtered = df[df["process"] == process.strip().lower()]
    return sorted(filtered["spec"].dropna().unique().tolist())

def load_issuers():
    df = load_familiar_specs()
    issuers = df["issuer"].dropna().unique().tolist()
    return sorted(set([i.strip() for i in issuers if i.strip()]))

def spec_exists(process, spec):
    df = load_familiar_specs()
    match = df[
        (df["process"].str.lower() == process.lower()) &
        (df["spec"].str.lower() == spec.lower())
    ]
    return not match.empty

def add_spec_entry(process, spec, issuer="", notes=""):
    df = load_familiar_specs()
    new_row = {
        "process": process.strip(),
        "spec": spec.strip(),
        "issuer": issuer.strip(),
        "notes": notes.strip()
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(SPECS_PATH, index=False)
