import os
import json
import yaml
import logging
import pandas as pd
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
    
    def __init__(self, vendor_file: str = None, vendor_options_file: str = None, contacts_file: str = None):
        """
        Initialize the vendor manager.
        
        Args:
            vendor_file: Path to the vendor JSON file. If None, uses default path.
            vendor_options_file: Path to the vendor options YAML file. If None, uses default path.
            contacts_file: Path to the contacts CSV file. If None, uses default path.
        """
        # Set default paths if not provided
        self.vendor_file = vendor_file or "config/vendors.json"
        self.vendor_options_file = vendor_options_file or "docs/OS/vendor_options.yaml"
        self.contacts_file = contacts_file or "docs/OS/contacts.csv"
        
        # Initialize validator for spec normalization
        self.validator = SpecValidator(self.vendor_options_file)
        
        # Load vendor data
        self.vendors = self.load_vendors(self.vendor_file)
        self.vendor_options = self.load_vendor_options(self.vendor_options_file)
        self.contacts = self.load_contacts(self.contacts_file)
    
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
    
    def _normalize_vendor_name(self, name: str) -> str:
        """
        Normalize vendor names to increase matching reliability.
        - Lowercase
        - Strip leading/trailing spaces
        - Replace various hyphens/dashes with a simple '-'
        - Collapse multiple whitespace to single space
        - Remove common company suffixes and punctuation (., , Inc, LLC, Co, Corp)
        """
        if not name:
            return ""
        import re
        n = str(name).strip().lower()
        # normalize dashes
        n = n.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
        # collapse whitespace
        n = re.sub(r"\s+", " ", n)
        # remove punctuation commas and periods
        n = n.replace(",", "").replace(".", "")
        # remove common suffixes
        for suf in [" inc", " inc.", " llc", " llc.", " co", " co.", " corp", " corp.", " corporation", " ltd", " ltd."]:
            if n.endswith(suf):
                n = n[: -len(suf)]
                n = n.strip()
        return n
    
    def load_contacts(self, contacts_file: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load vendor contacts from CSV file.
        
        Args:
            contacts_file: Path to the contacts CSV file
            
        Returns:
            Dictionary mapping vendor names to lists of contact dictionaries
        """
        contacts_by_vendor = {}
        self._contacts_by_norm: Dict[str, List[Dict[str, Any]]] = {}
        
        try:
            if not os.path.exists(contacts_file):
                logger.warning(f"Contacts file not found: {contacts_file}")
                return contacts_by_vendor
                
            # Load contacts CSV with different encodings
            try:
                # First try UTF-8
                df = pd.read_csv(contacts_file, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    # Then try Latin-1 (a more permissive encoding)
                    df = pd.read_csv(contacts_file, encoding='latin-1')
                    logger.info(f"Loaded contacts file using latin-1 encoding")
                except Exception as e:
                    # Finally try with errors='replace' to handle problematic characters
                    df = pd.read_csv(contacts_file, encoding='utf-8', errors='replace')
                    logger.info(f"Loaded contacts file using utf-8 with error replacement")
            
            # Clean up column names and data
            df.columns = [col.strip() for col in df.columns]
            
            # Helper function to safely convert values to string and strip
            def safe_str_strip(value):
                if pd.isna(value):  # Handle NaN values
                    return ""
                return str(value).strip()
            
            # Helper function to safely check if a value is primary
            def is_primary(value):
                if pd.isna(value):
                    return False
                return safe_str_strip(value).lower() == 'primary'
            
            # Group contacts by vendor
            for _, row in df.iterrows():
                vendor_name = safe_str_strip(row.get('Vendor', ''))
                if not vendor_name:
                    continue
                
                # Create contact dictionary
                contact = {
                    'name': safe_str_strip(row.get('Contact', '')),
                    'first_name': safe_str_strip(row.get('First', '')),
                    'last_name': safe_str_strip(row.get('Last', '')),
                    'email': safe_str_strip(row.get('Email', '')),
                    'phone': safe_str_strip(row.get('Phone', '')),
                    'type': safe_str_strip(row.get('type', '')),
                    'state': safe_str_strip(row.get('State', '')),
                    'primary': is_primary(row.get('P/S', '')),
                    'website': safe_str_strip(row.get('website', ''))
                }
                
                # Add to contacts dictionary (original key)
                if vendor_name not in contacts_by_vendor:
                    contacts_by_vendor[vendor_name] = []
                contacts_by_vendor[vendor_name].append(contact)
                
                # Also index by normalized name for robust lookup
                norm = self._normalize_vendor_name(vendor_name)
                if norm:
                    self._contacts_by_norm.setdefault(norm, []).append(contact)
            
            logger.info(f"Loaded {len(contacts_by_vendor)} vendors with contacts from {contacts_file}")
            # Log distinct normalized vendors as debug for diagnostics
            try:
                logger.debug(f"Normalized vendors count: {len(self._contacts_by_norm)}")
            except Exception:
                pass
            return contacts_by_vendor
            
        except Exception as e:
            logger.error(f"Error loading contacts file {contacts_file}: {str(e)}")
            return contacts_by_vendor
    
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
        
        First checks the contacts loaded from CSV file, then falls back to contacts in the vendor JSON.
        
        Args:
            vendor: Vendor dictionary
            
        Returns:
            Primary contact dictionary or first contact if no primary is specified
        """
        vendor_name = vendor.get('name', '')
        
        # First try to get contacts from CSV with exact match
        if vendor_name in self.contacts:
            csv_contacts = self.contacts[vendor_name]
            
            # Look for primary contact
            for contact in csv_contacts:
                if contact.get('primary', False):
                    return contact
            
            # If no primary contact found, return the first one
            if csv_contacts:
                return csv_contacts[0]
        
        # If no exact match, try case-insensitive match
        vendor_name_lower = vendor_name.lower()
        for csv_vendor_name, csv_contacts in self.contacts.items():
            if csv_vendor_name.lower() == vendor_name_lower:
                # Look for primary contact
                for contact in csv_contacts:
                    if contact.get('primary', False):
                        return contact
                
                # If no primary contact found, return the first one
                if csv_contacts:
                    return csv_contacts[0]
        
        # Try normalized name lookup
        try:
            norm_contacts = self.get_contacts_for_vendor(vendor_name)
            if norm_contacts:
                for contact in norm_contacts:
                    if contact.get('primary', False):
                        return contact
                return norm_contacts[0]
        except Exception:
            pass
                    
        # Try partial matching for special cases
        if "Turn-key" in vendor_name:
            # Look for "TURNKEY Coatings" in CSV
            if "TURNKEY Coatings" in self.contacts:
                csv_contacts = self.contacts["TURNKEY Coatings"]
                # Look for primary contact
                for contact in csv_contacts:
                    if contact.get('primary', False):
                        return contact
                
                # If no primary contact found, return the first one
                if csv_contacts:
                    return csv_contacts[0]
        
        # Try the reverse case
        if "TURNKEY" in vendor_name:
            # Look for vendors with "Turn-key" in the name
            for csv_vendor_name, csv_contacts in self.contacts.items():
                if "Turn-key" in csv_vendor_name:
                    # Look for primary contact
                    for contact in csv_contacts:
                        if contact.get('primary', False):
                            return contact
                    
                    # If no primary contact found, return the first one
                    if csv_contacts:
                        return csv_contacts[0]
                        
        # Try a more general approach for any vendor with "turn" or "key" in the name
        vendor_name_lower = vendor_name.lower()
        if "turn" in vendor_name_lower and "key" in vendor_name_lower:
            for csv_vendor_name, csv_contacts in self.contacts.items():
                csv_vendor_name_lower = csv_vendor_name.lower()
                if "turn" in csv_vendor_name_lower and "key" in csv_vendor_name_lower:
                    # Look for primary contact
                    for contact in csv_contacts:
                        if contact.get('primary', False):
                            return contact
                    
                    # If no primary contact found, return the first one
                    if csv_contacts:
                        return csv_contacts[0]
        
        # Fall back to contacts in vendor JSON
        json_contacts = vendor.get('contacts', [])
        for contact in json_contacts:
            if contact.get('primary', False):
                return contact
        
        # If no contacts found in either source, return None or the first JSON contact
        if not json_contacts:
            logger.warning(f"No valid contact found for vendor: {vendor_name}")
            return None
        
        return json_contacts[0]
    
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
    
    # Public helper to fetch contacts with normalization-aware lookup
    def get_contacts_for_vendor(self, vendor_name: str) -> List[Dict[str, Any]]:
        if not vendor_name:
            return []
        norm = self._normalize_vendor_name(vendor_name)
        # Prefer normalized index if available
        contacts = []
        try:
            contacts = self._contacts_by_norm.get(norm, [])
        except Exception:
            contacts = []
        if contacts:
            return contacts
        # Fallback to case-insensitive exact match over original keys
        v_lower = vendor_name.lower()
        for k, v in self.contacts.items():
            if k.lower() == v_lower:
                return v
        return []
    
    def reload_vendors(self):
        """Reload vendor data from files."""
        self.vendors = self.load_vendors(self.vendor_file)
        self.vendor_options = self.load_vendor_options(self.vendor_options_file)
        self.contacts = self.load_contacts(self.contacts_file)