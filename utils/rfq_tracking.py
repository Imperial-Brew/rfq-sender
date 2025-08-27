import os
import csv
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import pandas as pd
from datetime import datetime

from core.config import Paths, init_config, LoggingConfig

# Ensure configuration initialized
init_config()

logger = LoggingConfig.setup_logging(__name__, "rfq_tracking.log")


class RFQTracking:
    """
    Utility to manage rfq_master.csv and rfq_responses.csv based on templates.

    Files:
      - templates: docs/rfq_master_template.csv, docs/rfq_responses_template.csv
      - working:  docs/rfq_master.csv, docs/rfq_responses.csv
    """

    def __init__(self,
                 base_docs_dir: Optional[Path] = None,
                 contacts_csv: Optional[Path] = None):
        root_dir = Path(getattr(Paths, "ROOT_DIR", Path(__file__).resolve().parents[1]))
        self.base_docs_dir = Path(base_docs_dir) if base_docs_dir else (root_dir / "docs")
        # Templates
        self.master_tmpl = self.base_docs_dir / "rfq_master_template.csv"
        self.responses_tmpl = self.base_docs_dir / "rfq_responses_template.csv"
        # Working files
        self.master_path = self.base_docs_dir / "rfq_master.csv"
        self.responses_path = self.base_docs_dir / "rfq_responses.csv"
        # Contacts
        self.contacts_csv = Path(contacts_csv) if contacts_csv else (self.base_docs_dir / "OS" / "contacts.csv")

        # Ensure directories exist
        self.base_docs_dir.mkdir(parents=True, exist_ok=True)
        # Ensure files exist with headers copied from templates
        self._ensure_file_from_template(self.master_path, self.master_tmpl)
        self._ensure_file_from_template(self.responses_path, self.responses_tmpl)

        # Load contacts dataframe for validation
        self.contacts_df = self._load_contacts()

    def _ensure_file_from_template(self, dest: Path, template: Path) -> None:
        if dest.exists():
            return
        # Create file: if template exists copy header row; else create minimal header
        if template.exists():
            try:
                with open(template, "r", newline="", encoding="utf-8") as fin:
                    reader = csv.reader(fin)
                    rows = list(reader)
                header = rows[0] if rows else []
            except Exception:
                header = []
        else:
            header = []
        try:
            with open(dest, "w", newline="", encoding="utf-8") as fout:
                writer = csv.writer(fout)
                # Provide a sensible default header if template empty
                if not header:
                    header = [
                        "rfq#", "date", "qt/so #", "part_number", "process", "spec", "quantities",
                        "vendor", "contact", "rfq_folder", "status", "notes"
                    ]
                writer.writerow(header)
            logger.info(f"Initialized RFQ file from template: {dest}")
        except Exception as e:
            logger.error(f"Failed to initialize {dest}: {e}")

    def _load_contacts(self) -> pd.DataFrame:
        try:
            if not self.contacts_csv.exists():
                logger.warning(f"Contacts file not found: {self.contacts_csv}")
                return pd.DataFrame()
            try:
                df = pd.read_csv(self.contacts_csv, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(self.contacts_csv, encoding="cp1252")
            return df
        except Exception as e:
            logger.error(f"Error loading contacts: {e}")
            return pd.DataFrame()

    def _next_rfq_num(self) -> int:
        """Return the next integer rfq# based on existing master."""
        try:
            if not self.master_path.exists():
                return 1
            df = pd.read_csv(self.master_path, encoding="utf-8")
            # Normalize possible column names
            cols = [c.lower() for c in df.columns]
            if "rfq#" in cols:
                col = df.columns[cols.index("rfq#")]
            elif "rfq #" in cols:
                col = df.columns[cols.index("rfq #")]
            else:
                return 1
            # Coerce to numeric and find max
            nums = pd.to_numeric(df[col], errors="coerce").dropna()
            if nums.empty:
                return 1
            return int(nums.max()) + 1
        except Exception:
            return 1

    def _validate_vendor_contact(self, vendor_name: str, contact_email: str) -> Tuple[bool, str]:
        """
        Validate that vendor and contact exist in contacts.csv.
        Returns (is_valid, message)
        """
        try:
            df = self.contacts_df
            if df.empty:
                return False, "contacts.csv not loaded"
            # Normalize columns
            cols = {c.lower(): c for c in df.columns}
            vendor_col = cols.get("vendor")
            email_col = cols.get("email")
            if not vendor_col or not email_col:
                return False, "contacts.csv missing Vendor/Email columns"
            subset = df[(df[vendor_col].astype(str).str.strip() == str(vendor_name).strip()) &
                        (df[email_col].astype(str).str.strip().str.lower() == str(contact_email).strip().lower())]
            if subset.empty:
                return False, "no matching vendor/contact"
            return True, "ok"
        except Exception as e:
            return False, str(e)

    def add_master_entry(self,
                         queue_row: Dict[str, Any],
                         *,
                         vendor_name: str,
                         contact_email: str,
                         contact_name: Optional[str] = None,
                         status: str = "pending",
                         rfq_folder_link: Optional[str] = None,
                         notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Append a row to rfq_master.csv using template columns.
        Ensures unique rfq#.
        """
        # Load header from working master file
        try:
            with open(self.master_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
        except Exception:
            header = []

        # Prepare values from queue row
        qt_so = str(queue_row.get("qt/so #", "") or "")
        part_number = str(queue_row.get("part_number", "") or "")
        process = str(queue_row.get("process", "") or "")
        spec = str(queue_row.get("spec", "") or "")
        quantities = str(queue_row.get("quantities", "") or "")
        # Prefer quote-level link, fallback to part-level share link
        rfq_folder = rfq_folder_link or str(queue_row.get("box_rfq_folder", "") or queue_row.get("box_share_link", "") or "")

        # Validate vendor/contact
        ok, msg = self._validate_vendor_contact(vendor_name, contact_email)

        # Assign rfq#
        rfq_num = self._next_rfq_num()

        # Map values to potential columns
        values_map = {
            "rfq#": rfq_num,
            "rfq #": rfq_num,
            "date": datetime.now().isoformat(timespec="seconds"),
            "qt/so #": qt_so,
            "part_number": part_number,
            "process": process,
            "spec": spec,
            "quantities": quantities,
            "vendor": vendor_name,
            "contact": contact_email if contact_email else (contact_name or ""),
            "rfq_folder": rfq_folder,
            "status": status,
            "notes": notes or "",
            "validation_status": "ok" if ok else f"mismatch: {msg}",
        }

        # Build the row aligned to header; if header empty, use values_map keys order
        if not header:
            header = list(values_map.keys())
            # ensure master file has header
            with open(self.master_path, "w", newline="", encoding="utf-8") as fout:
                writer = csv.writer(fout)
                writer.writerow(header)

        row = [values_map.get(col, "") for col in header]

        # Append to file
        with open(self.master_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        logger.info(f"Appended RFQ master row rfq#={rfq_num} vendor={vendor_name} contact={contact_email}")
        return {"rfq#": rfq_num, "validation_ok": ok}

    def ensure_responses_file(self) -> None:
        """Ensure responses file exists; no-op otherwise."""
        self._ensure_file_from_template(self.responses_path, self.responses_tmpl)


# Convenience function
_default_tracker: Optional[RFQTracking] = None

def get_tracker() -> RFQTracking:
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = RFQTracking()
    return _default_tracker
