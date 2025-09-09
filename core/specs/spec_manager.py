import pandas as pd
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

class SpecManager:
    """
    Manages specification-related operations.
    
    This class provides functionality to:
    1. Load and manage familiar specs
    2. Get process lists and specs for processes
    3. Add new spec entries
    4. Check if specs exist
    """
    
    def __init__(self, specs_path: str = None, box_file_id: Optional[str] = None):
        """
        Initialize the spec manager.
        
        Args:
            specs_path: Path to the specs CSV file. If None, uses default path.
            box_file_id: Optional Box file ID for FamiliarSpecs.csv. When
                provided and Box can be initialized, the manager will read from
                and write to this Box file instead of the local CSV.
        """
        # Get the project root directory
        self.root_dir = Path(__file__).parent.parent.parent
        
        # Set default path if not provided
        self.specs_path = specs_path or os.path.join(
            self.root_dir, "docs", "OS", "spec_lists", "FamiliarSpecs.csv"
        )
        
        # Accept Box file id from param or environment/secrets.
        # Prefer explicit parameter; otherwise, honor environment/secrets ID
        # regardless of whether a local specs_path is provided. This avoids
        # accidental fallback to local when the Box ID is configured.
        env_id = (
            os.environ.get("BOX_FAMILIAR_SPECS_FILE_ID", "").strip()
            or os.environ.get("BOX_BOX_FAMILIAR_SPECS_FILE_ID", "").strip()
        )
        if box_file_id is not None:
            # Caller explicitly decided the ID (may be empty/None to force local)
            self.box_file_id = box_file_id or None
        else:
            # Use env/secrets-discovered ID whenever present
            self.box_file_id = env_id or None

        # Store the most recent reason for failing to load specs
        self.last_load_reason: Optional[str] = None
    
    def _load_from_box(self) -> Optional[pd.DataFrame]:
        """Attempt to load familiar specs CSV from Box if configured.

        Returns:
            DataFrame if successful, else None.
        """
        logger = logging.getLogger(__name__)
        if not self.box_file_id:
            msg = "Box file ID not configured; skipping Box load."
            logger.warning(msg)
            self.last_load_reason = msg
            return None
        try:
            # Lazy import to avoid hard dependency
            from scripts.box.box_integration import BoxIntegration
            box = BoxIntegration()
            client = getattr(box, "client", None)
            if not client:
                msg = "Box client not available; cannot load familiar specs."
                logger.warning(msg)
                self.last_load_reason = msg
                return None
            file_obj = client.file(self.box_file_id)
            try:
                content: bytes = file_obj.content()
            except Exception as e:
                msg = f"Failed to fetch familiar specs from Box: {e}"
                logger.warning(msg)
                self.last_load_reason = msg
                return None
            from io import BytesIO
            df = pd.read_csv(BytesIO(content))
            df.columns = df.columns.str.strip().str.lower()
            self.last_load_reason = None
            return df
        except Exception as e:
            msg = f"Failed to load familiar specs from Box: {e}"
            try:
                logger.exception(msg)
            except Exception:
                pass
            self.last_load_reason = msg
            return None
    
    def _save_to_box(self, df: pd.DataFrame) -> bool:
        """Attempt to upload the familiar specs CSV to Box if configured.
        Overwrites the existing file by uploading a new version.
        
        Returns:
            True on success, False otherwise.
        """
        try:
            if not self.box_file_id:
                return False
            from scripts.box.box_integration import BoxIntegration
            box = BoxIntegration()
            client = getattr(box, "client", None)
            if not client:
                return False
            # Serialize DataFrame to CSV bytes
            from io import BytesIO
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            file_obj = client.file(self.box_file_id)
            # boxsdk 3.14.0: update_contents_with_stream does not accept file_size kwarg
            # Passing file_size raises TypeError before any network request; remove for compatibility.
            file_obj.update_contents_with_stream(BytesIO(csv_bytes))
            return True
        except Exception as e:
            try:
                logging.getLogger(__name__).exception("Failed to save familiar specs to Box")
            except Exception:
                pass
            return False
    
    def load_familiar_specs(self) -> pd.DataFrame:
        """
        Load familiar specs from Box (if configured) or local CSV.
        
        Returns:
            DataFrame containing familiar specs
        """
        # Try Box first if configured
        box_df = self._load_from_box()
        if isinstance(box_df, pd.DataFrame):
            return box_df

        # Fallback to local file
        if not os.path.exists(self.specs_path):
            msg = f"Local familiar specs file not found: {self.specs_path}"
            logging.getLogger(__name__).warning(msg)
            if not self.last_load_reason:
                self.last_load_reason = msg
            return pd.DataFrame(columns=["process", "spec", "issuer", "notes"])

        try:
            df = pd.read_csv(self.specs_path)
            df.columns = df.columns.str.strip().str.lower()  # Normalize headers
            self.last_load_reason = None
            return df
        except Exception as e:
            msg = f"Failed to load familiar specs from local file: {e}"
            logging.getLogger(__name__).error(msg)
            self.last_load_reason = msg
            return pd.DataFrame(columns=["process", "spec", "issuer", "notes"])
    
    def load_process_list(self) -> List[str]:
        """
        Get a list of all unique processes.
        
        Returns:
            List of process names
        """
        df = self.load_familiar_specs()
        return df["process"].dropna().unique().tolist()
    
    def load_specs_for_process(self, process: Optional[str]) -> List[str]:
        """
        Get a list of specs for a specific process.
        
        Args:
            process: Process name to filter by. If None or empty, returns [].
            
        Returns:
            List of spec names for the process
        """
        df = self.load_familiar_specs()
        if "process" not in df.columns or "spec" not in df.columns:
            return []

        # Normalize casing and spacing for matching
        df["process"] = df["process"].astype(str).str.strip().str.lower()
        df["spec"] = df["spec"].astype(str).str.strip()

        # Safely handle None or empty process input
        if process is None:
            return []
        safe_process = str(process).strip().lower()
        if not safe_process:
            return []

        filtered = df[df["process"] == safe_process]
        return sorted(filtered["spec"].dropna().unique().tolist())
    
    def load_issuers(self) -> List[str]:
        """
        Get a list of all unique issuers.
        
        Returns:
            List of issuer names
        """
        df = self.load_familiar_specs()
        issuers = df["issuer"].dropna().unique().tolist()
        return sorted(set([i.strip() for i in issuers if i.strip()]))
    
    def spec_exists(self, process: str, spec: str) -> bool:
        """
        Check if a spec exists for a specific process.
        
        Args:
            process: Process name
            spec: Spec name
            
        Returns:
            True if the spec exists for the process, False otherwise
        """
        df = self.load_familiar_specs()
        match = df[
            (df["process"].str.lower() == process.lower()) &
            (df["spec"].str.lower() == spec.lower())
        ]
        return not match.empty
    
    def add_spec_entry(self, process: str, spec: str, issuer: str = "", notes: str = "") -> bool:
        """
        Add a new spec entry.
        
        Args:
            process: Process name
            spec: Spec name
            issuer: Issuer name (optional)
            notes: Additional notes (optional)
            
        Returns:
            True if the entry was added successfully, False otherwise
        """
        try:
            df = self.load_familiar_specs()
            new_row = {
                "process": process.strip(),
                "spec": spec.strip(),
                "issuer": issuer.strip(),
                "notes": notes.strip()
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(self.specs_path, index=False)
            return True
        except Exception as e:
            # Log the error
            print(f"Error adding spec entry: {str(e)}")
            return False
