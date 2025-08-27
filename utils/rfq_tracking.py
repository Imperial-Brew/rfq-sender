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
      - working:  docs/rfq_master.csv, docs/rfq_responses.csv (local fallback)
      - Box-backed when configured via secrets/env (preferred)
    """

    def __init__(self,
                 base_docs_dir: Optional[Path] = None,
                 contacts_csv: Optional[Path] = None):
        root_dir = Path(getattr(Paths, "ROOT_DIR", Path(__file__).resolve().parents[1]))
        self.base_docs_dir = Path(base_docs_dir) if base_docs_dir else (root_dir / "docs")
        # Templates
        self.master_tmpl = self.base_docs_dir / "rfq_master_template.csv"
        self.responses_tmpl = self.base_docs_dir / "rfq_responses_template.csv"
        # Working files (local fallback paths)
        self.master_path = self.base_docs_dir / "rfq_master.csv"
        self.responses_path = self.base_docs_dir / "rfq_responses.csv"
        # Contacts
        self.contacts_csv = Path(contacts_csv) if contacts_csv else (self.base_docs_dir / "OS" / "contacts.csv")

        # Attempt to configure Box stores for master and responses
        self.master_store = None
        self.responses_store = None
        try:
            from scripts.box.box_integration import BoxIntegration
            from scripts.box.box_csv_store import BoxCSVStore
            # Pull IDs from env or secrets
            import os as _os
            file_id_master = _os.environ.get("BOX_RFQ_MASTER_FILE_ID", "").strip() or _os.environ.get("BOX_BOX_RFQ_MASTER_FILE_ID", "").strip()
            folder_id_master = _os.environ.get("BOX_RFQ_MASTER_FOLDER_ID", "").strip() or _os.environ.get("BOX_BOX_RFQ_MASTER_FOLDER_ID", "").strip()
            file_id_resp = _os.environ.get("BOX_RFQ_RESPONSES_FILE_ID", "").strip() or _os.environ.get("BOX_BOX_RFQ_RESPONSES_FILE_ID", "").strip()
            folder_id_resp = _os.environ.get("BOX_RFQ_RESPONSES_FOLDER_ID", "").strip() or _os.environ.get("BOX_BOX_RFQ_RESPONSES_FOLDER_ID", "").strip()
            # Try secrets [box] too
            if not (file_id_master or folder_id_master or file_id_resp or folder_id_resp):
                try:
                    from core.secrets import get_section as _get_secret_section
                    _boxsec = _get_secret_section("box") or {}
                    file_id_master = file_id_master or str(_boxsec.get("BOX_RFQ_MASTER_FILE_ID", "")).strip()
                    folder_id_master = folder_id_master or str(_boxsec.get("BOX_RFQ_MASTER_FOLDER_ID", "")).strip()
                    file_id_resp = file_id_resp or str(_boxsec.get("BOX_RFQ_RESPONSES_FILE_ID", "")).strip()
                    folder_id_resp = folder_id_resp or str(_boxsec.get("BOX_RFQ_RESPONSES_FOLDER_ID", "")).strip()
                except Exception:
                    pass
            # Initialize Box only if we have at least one target configured
            if (file_id_master or folder_id_master or file_id_resp or folder_id_resp):
                box = BoxIntegration(logger=logger)
                if getattr(box, "client", None):
                    # Prepare headers from templates (first row)
                    master_header = self._template_header(self.master_tmpl, default=[
                        "rfq#", "date", "qt/so #", "part_number", "process", "spec", "quantities",
                        "vendor", "contact", "rfq_folder", "status", "notes"
                    ])
                    responses_header = self._template_header(self.responses_tmpl, default=[])
                    if file_id_master or folder_id_master:
                        self.master_store = BoxCSVStore(
                            box_integration=box,
                            filename="rfq_master.csv",
                            file_id=(file_id_master or None),
                            folder_id=(folder_id_master or None),
                            header=master_header,
                            logger=logger,
                        )
                    if file_id_resp or folder_id_resp:
                        self.responses_store = BoxCSVStore(
                            box_integration=box,
                            filename="rfq_responses.csv",
                            file_id=(file_id_resp or None),
                            folder_id=(folder_id_resp or None),
                            header=responses_header,
                            logger=logger,
                        )
                else:
                    logger.warning("Box initialization failed for RFQ tracking; using local CSV fallback.")
        except Exception as _e:
            logger.debug(f"RFQTracking Box store init skipped or failed: {_e}")

        # Ensure directories exist (for local fallback)
        self.base_docs_dir.mkdir(parents=True, exist_ok=True)
        # Ensure files exist with headers copied from templates (local), if Box not used
        if self.master_store is None:
            self._ensure_file_from_template(self.master_path, self.master_tmpl)
        if self.responses_store is None:
            self._ensure_file_from_template(self.responses_path, self.responses_tmpl)

        # Load contacts dataframe for validation
        self.contacts_df = self._load_contacts()

    def _template_header(self, template: Path, default: list) -> list:
        """Return header list from template or provided default."""
        header = []
        try:
            if template.exists():
                with open(template, "r", newline="", encoding="utf-8") as fin:
                    reader = csv.reader(fin)
                    rows = list(reader)
                header = rows[0] if rows else []
        except Exception:
            header = []
        return header or default

    def _ensure_file_from_template(self, dest: Path, template: Path) -> None:
        if dest.exists():
            return
        header = self._template_header(template, default=[
            "rfq#", "date", "qt/so #", "part_number", "process", "spec", "quantities",
            "vendor", "contact", "rfq_folder", "status", "notes"
        ])
        try:
            with open(dest, "w", newline="", encoding="utf-8") as fout:
                writer = csv.writer(fout)
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
        # Determine header either from existing Box/local file or template
        header: list = []
        if self.master_store is not None:
            try:
                existing_df = self.master_store.load_df()
                header = list(existing_df.columns)
            except Exception:
                header = []
        if not header:
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

        # Append to file (Box preferred)
        try:
            if self.master_store is not None:
                df = self.master_store.load_df()
                # if header known but df empty without columns, set columns
                if df is None or df.empty:
                    df = pd.DataFrame(columns=header)
                # Convert row to dict with headers
                new_row_dict = {col: values_map.get(col, "") for col in header}
                df = pd.concat([df, pd.DataFrame([new_row_dict])], ignore_index=True)
                self.master_store.save_df(df)
            else:
                with open(self.master_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(row)
        except Exception as _e:
            logger.error(f"Failed to append RFQ master row (rfq#={rfq_num}) to Box; falling back to local. Err: {_e}")
            try:
                with open(self.master_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(row)
            except Exception as _e2:
                logger.error(f"Also failed local append for rfq#={rfq_num}: {_e2}")

        logger.info(f"Appended RFQ master row rfq#={rfq_num} vendor={vendor_name} contact={contact_email}")
        return {"rfq#": rfq_num, "validation_ok": ok}

    def ensure_responses_file(self) -> None:
        """Ensure responses file exists in Box if configured; else locally."""
        if self.responses_store is not None:
            try:
                # Loading ensures creation with header in Box store
                _ = self.responses_store.load_df()
                return
            except Exception as _e:
                logger.warning(f"Failed to ensure responses file in Box: {_e}; falling back to local.")
        self._ensure_file_from_template(self.responses_path, self.responses_tmpl)


# Convenience function
_default_tracker: Optional[RFQTracking] = None

def get_tracker() -> RFQTracking:
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = RFQTracking()
    return _default_tracker
