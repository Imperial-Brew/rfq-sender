import yaml
import os
import unicodedata
import re
from difflib import get_close_matches
from typing import Dict, List, Set, Tuple, Optional, Any, Union


class SpecValidator:
    """
    A tool for validating and normalizing process and spec names against a reference.

    This class provides functionality to:
    1. Check if a process or spec exists in the reference
    2. Normalize process and spec names (remove whitespace, standardize format)
    3. Suggest similar processes or specs using fuzzy matching
    4. Add new processes or specs to the reference
    """

    def __init__(self, yaml_path: str = None):
        """
        Initialize the validator with a reference YAML file.

        Args:
            yaml_path: Path to the vendor_options.yaml file. If None, will look in default locations.
        """
        if yaml_path is None:
            # Try to find the yaml file in common locations
            possible_paths = [
                'vendor_options.yaml',
                'docs/OS/vendor_options.yaml',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'OS', 'vendor_options.yaml')
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    yaml_path = path
                    break

            if yaml_path is None:
                raise FileNotFoundError("Could not find vendor_options.yaml in default locations")

        # Load the reference data
        with open(yaml_path, 'r', encoding='utf-8') as f:
            self.ref = yaml.safe_load(f)

        self.yaml_path = yaml_path

        # Extract processes and specs
        self.processes = {p['name'] for v in self.ref['vendors'] for p in v.get('processes', [])}
        self.specs = {s['number'] for v in self.ref['vendors']
                      for p in v.get('processes', [])
                      for s in (p.get('specs') or [])}

        # Build normalized maps
        self._build_normalized_maps()

    def _build_normalized_maps(self):
        """Build maps from normalized text to original text."""
        self.norm_to_proc = {self.normalize(p): p for p in self.processes}
        self.norm_to_spec = {self.normalize(s): s for s in self.specs}

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize text by removing extra whitespace, standardizing dashes, etc.

        Args:
            text: The text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Convert to string if not already
        text = str(text)

        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)

        # Replace various dash characters with standard dash
        text = text.replace('—', '-').replace('–', '-').replace('�', '-')

        # Remove trailing commas and periods
        text = text.rstrip(',.;:')

        # Replace multiple spaces with a single space
        text = ' '.join(text.split())

        # Remove "per" and surrounding whitespace if it exists
        text = re.sub(r'\s+per\s+', ' ', text, flags=re.IGNORECASE)

        # Strip whitespace and convert to lowercase
        return text.strip().lower()

    def check_process(self, process: str) -> Tuple[bool, str, List[str]]:
        """
        Check if a process exists in the reference.

        Args:
            process: The process name to check

        Returns:
            Tuple containing:
                - Whether the process exists (after normalization)
                - The normalized process name
                - List of suggested matches if not found
        """
        norm_process = self.normalize(process)

        # Check for exact match after normalization
        if norm_process in self.norm_to_proc:
            return True, self.norm_to_proc[norm_process], []

        # If no exact match, get fuzzy matches
        matches = get_close_matches(norm_process, self.norm_to_proc.keys(), n=3, cutoff=0.6)
        suggestions = [self.norm_to_proc[m] for m in matches]

        return False, norm_process, suggestions

    def check_spec(self, spec: str) -> Tuple[bool, str, List[str]]:
        """
        Check if a spec exists in the reference.

        Args:
            spec: The spec name to check

        Returns:
            Tuple containing:
                - Whether the spec exists (after normalization)
                - The normalized spec name
                - List of suggested matches if not found
        """
        norm_spec = self.normalize(spec)

        # Check for exact match after normalization
        if norm_spec in self.norm_to_spec:
            return True, self.norm_to_spec[norm_spec], []

        # If no exact match, get fuzzy matches
        matches = get_close_matches(norm_spec, self.norm_to_spec.keys(), n=3, cutoff=0.6)
        suggestions = [self.norm_to_spec[m] for m in matches]

        return False, norm_spec, suggestions

    def add_process(self, process: str, vendor_name: str = None) -> bool:
        """
        Add a new process to the reference.

        Args:
            process: The process name to add
            vendor_name: The name of the vendor to add the process to. If None, adds to all vendors.

        Returns:
            Whether the process was added successfully
        """
        # Normalize the process name
        norm_process = self.normalize(process)

        # Check if the process already exists
        if norm_process in self.norm_to_proc:
            return False

        # Add the process to the specified vendor or all vendors
        if vendor_name:
            for vendor in self.ref['vendors']:
                if vendor['name'] == vendor_name:
                    vendor['processes'].append({'name': process, 'specs': []})
                    break
        else:
            # If no vendor specified, add to the first vendor
            if self.ref['vendors']:
                self.ref['vendors'][0]['processes'].append({'name': process, 'specs': []})

        # Save the updated reference
        self._save_reference()

        # Rebuild the normalized maps
        self._build_normalized_maps()

        return True

    def add_spec(self, spec: str, process_name: str, vendor_name: str = None) -> bool:
        """
        Add a new spec to the reference.

        Args:
            spec: The spec name to add
            process_name: The name of the process to add the spec to
            vendor_name: The name of the vendor to add the spec to. If None, adds to all vendors with the process.

        Returns:
            Whether the spec was added successfully
        """
        # Normalize the spec name
        norm_spec = self.normalize(spec)

        # Check if the spec already exists
        if norm_spec in self.norm_to_spec:
            return False

        # Add the spec to the specified process in the specified vendor or all vendors
        added = False

        for vendor in self.ref['vendors']:
            if vendor_name and vendor['name'] != vendor_name:
                continue

            for process in vendor.get('processes', []):
                if self.normalize(process['name']) == self.normalize(process_name):
                    if process.get('specs') is None:
                        process['specs'] = []

                    process['specs'].append({'number': spec, 'familiar': True})
                    added = True

        if added:
            # Save the updated reference
            self._save_reference()

            # Rebuild the normalized maps
            self._build_normalized_maps()

        return added

    def _save_reference(self):
        """Save the reference data back to the YAML file."""
        with open(self.yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.ref, f, default_flow_style=False, sort_keys=False)