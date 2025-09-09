import pandas as pd
import os
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
    
    def __init__(self, specs_path: str = None):
        """
        Initialize the spec manager.
        
        Args:
            specs_path: Path to the specs CSV file. If None, uses default path.
        """
        # Get the project root directory
        self.root_dir = Path(__file__).parent.parent.parent
        
        # Set default path if not provided
        self.specs_path = specs_path or os.path.join(self.root_dir, "docs", "OS", "spec_lists", "FamiliarSpecs.csv")
    
    def load_familiar_specs(self) -> pd.DataFrame:
        """
        Load familiar specs from CSV file.
        
        Returns:
            DataFrame containing familiar specs
        """
        if not os.path.exists(self.specs_path):
            return pd.DataFrame(columns=["process", "spec", "issuer", "notes"])
            
        df = pd.read_csv(self.specs_path)
        df.columns = df.columns.str.strip().str.lower()  # Normalize headers
        return df
    
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