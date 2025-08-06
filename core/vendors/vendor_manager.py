import os
import json
import yaml
import logging
from typing import Dict, List, Optional, Any, Tuple
from core.validation.validator import SpecValidator

# Set up logging
logger = logging.getLogger(__name__)

class VendorManager:
    """
    Manages vendor information and operations.
    
    This class provides functionality to:
    1. Load vendor information from JSON and YAML files
    2. Find vendors for specific processes and specs
    3. Get primary contacts for vendors
    """
    
    def __init__(self, vendor_file: str = None, vendor_options_file: str = None):
        """
        Initialize the vendor manager.
        
        Args:
            vendor_file: Path to the vendor JSON file. If None, uses default path.
            vendor_options_file: Path to the vendor options YAML file. If None, uses default path.
        """
        # Set default paths if not provided
        self.vendor_file = vendor_file or "config/vendors.json"
        self.vendor_options_file = vendor_options_file or "docs/OS/vendor_options.yaml"
        
        # Initialize validator for spec normalization
        self.validator = SpecValidator(self.vendor_options_file)
        
        # Load vendor data
        self.vendors = self.load_vendors(self.vendor_file)
        self.vendor_options = self.load_vendor_options(self.vendor_options_file)
    
    def load_vendors(self, vendor_file: str) -> List[Dict[str, Any]]:
        """
        Load vendor information from JSON file.
        
        Args:
            vendor_file: Path to the vendor JSON file
            
        Returns:
            List of vendor dictionaries
        """
        try:
            with open(vendor_file, 'r') as f:
                data = json.load(f)
            return data.get('vendors', [])
        except FileNotFoundError:
            logger.error(f"Vendor file not found: {vendor_file}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in vendor file {vendor_file}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error loading vendor file {vendor_file}: {str(e)}")
            return []
    
    def load_vendor_options(self, vendor_options_file: str) -> Dict[str, Any]:
        """
        Load vendor options from YAML file.
        
        Args:
            vendor_options_file: Path to the vendor options YAML file
            
        Returns:
            Dictionary containing vendor options data
        """
        try:
            with open(vendor_options_file, 'r', encoding='utf-8') as f:
                vendor_options = yaml.safe_load(f)
            return vendor_options
        except FileNotFoundError:
            logger.error(f"Vendor options file not found: {vendor_options_file}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in vendor options file {vendor_options_file}: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error loading vendor options file {vendor_options_file}: {str(e)}")
            return {}
    
    def find_vendors_for_process(self, process: str) -> List[Dict[str, Any]]:
        """
        Find vendors that support a specific process.
        
        Args:
            process: Process name to match
            
        Returns:
            List of vendor dictionaries that support the process
        """
        return [v for v in self.vendors if process.lower() in [p.lower() for p in v.get('processes', [])]]
    
    def find_vendors_for_process_and_spec(
            self,
            process: str,
            spec: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find vendors that support a specific process and spec.
        
        Args:
            process: Process name to match
            spec: Optional spec to match
            
        Returns:
            List of vendor dictionaries that support the process and spec
        """
        # If no spec provided, use the simple process-only filter
        if not spec:
            return self.find_vendors_for_process(process)
        
        # Normalize the input spec for comparison
        normalized_spec = self._normalize_process_spec(spec)
        
        # Find vendors that support this spec
        suitable_vendors = []
        vendor_names_by_spec = []
        
        # First try to find vendors by spec
        if "vendors" in self.vendor_options:
            for vendor_option in self.vendor_options["vendors"]:
                vendor_name = vendor_option.get("name", "")
                
                for vendor_process in vendor_option.get("processes", []):
                    if isinstance(vendor_process, dict) and vendor_process.get("name", "").lower() == process.lower():
                        # This vendor supports the process, now check if it supports the spec
                        if "specs" in vendor_process and vendor_process["specs"]:
                            for vendor_spec in vendor_process["specs"]:
                                if isinstance(vendor_spec, dict) and "number" in vendor_spec:
                                    # Normalize the vendor spec for comparison
                                    normalized_vendor_spec = self._normalize_process_spec(vendor_spec["number"])
                                    
                                    if normalized_spec == normalized_vendor_spec:
                                        # Found a match by spec
                                        vendor_names_by_spec.append(vendor_name)
                                        break
        
        # Now find the matching vendors in the original vendors list
        for vendor in self.vendors:
            if vendor.get("name") in vendor_names_by_spec:
                suitable_vendors.append(vendor)
        
        # If no vendors found by spec, fall back to process-only filtering
        if not suitable_vendors:
            return self.find_vendors_for_process(process)
        
        return suitable_vendors
    
    def get_primary_contact(self, vendor: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get the primary contact for a vendor.
        
        Args:
            vendor: Vendor dictionary
            
        Returns:
            Primary contact dictionary or first contact if no primary is specified
        """
        contacts = vendor.get('contacts', [])
        for contact in contacts:
            if contact.get('primary', False):
                return contact
        return contacts[0] if contacts else None
    
    def _normalize_process_spec(self, text: str) -> str:
        """
        Normalize a process or spec name for comparison.
        
        Args:
            text: The text to normalize
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Basic normalization
        normalized = text.lower().strip()
        normalized = normalized.replace("-", "").replace(" ", "")
        
        # Use validator for more advanced normalization
        try:
            normalized = self.validator.normalize(normalized)
        except Exception:
            pass
        
        return normalized
    
    def reload_vendors(self):
        """Reload vendor data from files."""
        self.vendors = self.load_vendors(self.vendor_file)
        self.vendor_options = self.load_vendor_options(self.vendor_options_file)