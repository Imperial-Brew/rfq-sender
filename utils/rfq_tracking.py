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
        """Return the next integer rfq# based on existing master (Box-first if configured)."""
        try:
            df = None
            # Prefer Box-backed master if configured and accessible
            if getattr(self, "master_store", None) is not None:
                try:
                    df = self.master_store.load_df()
                except Exception as _e:
                    logger.debug(f"Box load for rfq_master failed in _next_rfq_num: {_e}")
                    df = None
            # Fallback to local file if Box not used or failed
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                if not self.master_path.exists():
                    return 1
                try:
                    df = pd.read_csv(self.master_path, encoding="utf-8")
                except UnicodeDecodeError:
                    df = pd.read_csv(self.master_path, encoding="cp1252")
                except Exception as _e:
                    logger.debug(f"Local load for rfq_master failed in _next_rfq_num: {_e}")
                    return 1
            # Guard: empty dataframe
            if df is None or df.empty:
                return 1
            # Normalize possible column names
            cols_lower = [str(c).lower().strip() for c in df.columns]
            target_col = None
            if "rfq#" in cols_lower:
                target_col = df.columns[cols_lower.index("rfq#")]
            elif "rfq #" in cols_lower:
                target_col = df.columns[cols_lower.index("rfq #")]
            else:
                # Try to infer a numeric rfq-like column
                for cand in df.columns:
                    if str(cand).lower().replace(" ", "") in ("rfq#", "rfq#", "rfqno", "rfqid"):
                        target_col = cand
                        break
                if target_col is None:
                    return 1
            # Coerce to numeric and find max
            nums = pd.to_numeric(df[target_col], errors="coerce").dropna()
            if nums.empty:
                return 1
            return int(nums.max()) + 1
        except Exception as e:
            logger.debug(f"_next_rfq_num unexpected error: {e}")
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
                         notes: Optional[str] = None,
                         dedupe: bool = False,
                         on_duplicate: str = "skip") -> Dict[str, Any]:
        """
        Append a row to rfq_master.csv using template columns.
        Ensures unique rfq#.

        Parameters:
        - dedupe: when True, check existing rfq_master (Box-first) for a matching natural key
                  (qt/so #, part_number, process, vendor, contact) before inserting.
        - on_duplicate: behavior if a duplicate is found (one of: 'skip', 'update', 'append').
            'skip'   -> return existing rfq# without writing a new row.
            'update' -> update status/notes/rfq_folder/date on the existing row and return its rfq#.
            'append' -> always append a new row (behaves like dedupe=False).
        """
        # Determine header either from existing Box/local file or template
        header: list = []
        existing_df: Optional[pd.DataFrame] = None
        if self.master_store is not None:
            try:
                existing_df = self.master_store.load_df()
                header = list(existing_df.columns)
            except Exception:
                header = []
                existing_df = None
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

        # Helper to map logical to actual column names
        def _col(df: pd.DataFrame, name: str) -> Optional[str]:
            if df is None or df.empty:
                return None
            low = [str(c).lower().strip() for c in df.columns]
            key = name.lower().strip()
            return df.columns[low.index(key)] if key in low else None

        # Dedupe flow (Box-first, then local) if requested
        match_idx = None
        existing_rfq_num = None
        if dedupe and on_duplicate in ("skip", "update", "append"):
            # Load df if not already
            df = existing_df
            if df is None and self.master_path.exists():
                try:
                    df = pd.read_csv(self.master_path, encoding="utf-8")
                except UnicodeDecodeError:
                    df = pd.read_csv(self.master_path, encoding="cp1252")
                except Exception:
                    df = None
            if df is not None and not df.empty:
                # Resolve column names
                col_qt = _col(df, "qt/so #")
                col_part = _col(df, "part_number")
                col_proc = _col(df, "process")
                col_vendor = _col(df, "vendor")
                col_contact = _col(df, "contact")
                col_rfq = _col(df, "rfq#") or _col(df, "rfq #")
                # Only attempt match if all key cols exist
                if all([col_qt, col_part, col_proc, col_vendor, col_contact, col_rfq]):
                    def norm_series(s):
                        return s.astype(str).str.strip().str.lower()
                    try:
                        mask = (
                            norm_series(df[col_qt]) == qt_so.strip().lower()
                        ) & (
                            norm_series(df[col_part]) == part_number.strip().lower()
                        ) & (
                            norm_series(df[col_proc]) == process.strip().lower()
                        ) & (
                            norm_series(df[col_vendor]) == str(vendor_name).strip().lower()
                        ) & (
                            norm_series(df[col_contact]) == (str(contact_email or contact_name or "").strip().lower())
                        )
                        matches = df[mask]
                        if not matches.empty:
                            match_idx = matches.index[0]
                            try:
                                existing_rfq_num = int(pd.to_numeric(matches.iloc[0][col_rfq], errors="coerce"))
                            except Exception:
                                existing_rfq_num = None
                            # Handle duplicate per policy
                            if on_duplicate == "skip":
                                return {"rfq#": existing_rfq_num, "validation_ok": ok, "duplicate": True, "action": "skipped"}
                            elif on_duplicate == "update":
                                # Update fields on the existing row
                                now_iso = datetime.now().isoformat(timespec="seconds")
                                try:
                                    if status is not None and _col(df, "status"):
                                        df.loc[match_idx, _col(df, "status")] = status
                                except Exception:
                                    pass
                                try:
                                    if notes is not None and _col(df, "notes"):
                                        df.loc[match_idx, _col(df, "notes")] = notes
                                except Exception:
                                    pass
                                try:
                                    if rfq_folder and _col(df, "rfq_folder"):
                                        df.loc[match_idx, _col(df, "rfq_folder")] = rfq_folder
                                except Exception:
                                    pass
                                try:
                                    if _col(df, "date"):
                                        df.loc[match_idx, _col(df, "date")] = now_iso
                                except Exception:
                                    pass
                                # Save back
                                try:
                                    if self.master_store is not None:
                                        self.master_store.save_df(df)
                                    else:
                                        df.to_csv(self.master_path, index=False)
                                except Exception as _e:
                                    logger.warning(f"Failed to save updated duplicate RFQ in Box/local: {_e}")
                                return {"rfq#": existing_rfq_num, "validation_ok": ok, "duplicate": True, "action": "updated"}
                            # else on_duplicate == 'append' falls through to append
                    except Exception as _e:
                        logger.debug(f"Error during duplicate detection: {_e}")

        # Assign rfq# only when appending a new row
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
                df = existing_df if existing_df is not None else self.master_store.load_df()
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
        return {"rfq#": rfq_num, "validation_ok": ok, "duplicate": False, "action": "appended"}

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
