# Contacts CSV Implementation Summary

## Issue Description

The RFQ Sender application was previously using vendor contact information stored in the `vendors.json` file. The requirement was to modify the application to use contact information from the `docs/OS/contacts.csv` file instead, while maintaining backward compatibility.

## Changes Made

1. **Enhanced VendorManager Class**
   - Added a new `load_contacts` method to load contacts from CSV file
   - Updated the `get_primary_contact` method to prioritize contacts from CSV over those in JSON
   - Added a `contacts_file` parameter to the constructor with a default path
   - Ensured backward compatibility by falling back to JSON contacts if CSV contacts are not found

2. **Updated Email Utility Functions**
   - Modified `load_vendors` function to accept a `contacts_file` parameter
   - Updated `process_queue_and_send_emails` function to accept and use the `contacts_file` parameter
   - Maintained backward compatibility with existing code

3. **Updated Streamlit Application**
   - Modified the "Send RFQ Emails" page to load contacts from CSV
   - Updated both the selected parts and entire queue processing to use contacts from CSV

## Implementation Details

### VendorManager Class Updates

The `VendorManager` class in `core/vendors/vendor_manager.py` was enhanced to load and use contacts from CSV:

```python
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
```

A new `load_contacts` method was added to load contacts from CSV:

```python
def load_contacts(self, contacts_file: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load vendor contacts from CSV file.
    
    Args:
        contacts_file: Path to the contacts CSV file
        
    Returns:
        Dictionary mapping vendor names to lists of contact dictionaries
    """
    contacts_by_vendor = {}
    
    try:
        if not os.path.exists(contacts_file):
            logger.warning(f"Contacts file not found: {contacts_file}")
            return contacts_by_vendor
            
        # Load contacts CSV
        df = pd.read_csv(contacts_file)
        
        # Clean up column names and data
        df.columns = [col.strip() for col in df.columns]
        
        # Group contacts by vendor
        for _, row in df.iterrows():
            vendor_name = row.get('Vendor', '').strip()
            if not vendor_name:
                continue
            
            # Create contact dictionary
            contact = {
                'name': row.get('Contact', '').strip(),
                'first_name': row.get('First', '').strip(),
                'last_name': row.get('Last', '').strip(),
                'email': row.get('Email', '').strip(),
                'phone': row.get('Phone', '').strip(),
                'type': row.get('type', '').strip(),
                'state': row.get('State', '').strip(),
                'primary': row.get('P/S', '').strip().lower() == 'primary',
                'website': row.get('website', '').strip()
            }
            
            # Add to contacts dictionary
            if vendor_name not in contacts_by_vendor:
                contacts_by_vendor[vendor_name] = []
            contacts_by_vendor[vendor_name].append(contact)
        
        logger.info(f"Loaded {len(contacts_by_vendor)} vendors with contacts from {contacts_file}")
        return contacts_by_vendor
        
    except Exception as e:
        logger.error(f"Error loading contacts file {contacts_file}: {str(e)}")
        return contacts_by_vendor
```

The `get_primary_contact` method was updated to prioritize contacts from CSV:

```python
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
    
    # First try to get contacts from CSV
    if vendor_name in self.contacts:
        csv_contacts = self.contacts[vendor_name]
        
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
```

### Email Utility Updates

The `load_vendors` function in `utils/email.py` was updated to accept a `contacts_file` parameter:

```python
def load_vendors(vendor_file: str, contacts_file: str = None) -> List[Dict[str, Any]]:
    """
    Load vendor information from JSON file and contacts from CSV file.
    
    Args:
        vendor_file: Path to the vendor JSON file
        contacts_file: Path to the contacts CSV file (default: docs/OS/contacts.csv)
        
    Returns:
        List of vendor dictionaries
    """
    contacts_file = contacts_file or "docs/OS/contacts.csv"
    vendor_manager = VendorManager(vendor_file=vendor_file, contacts_file=contacts_file)
    return vendor_manager.vendors
```

The `process_queue_and_send_emails` function was updated to accept a `contacts_file` parameter:

```python
def process_queue_and_send_emails(
        queue_file: str = None,
        vendor_file: str = None,
        template_path: str = None,
        exchange_settings: Dict[str, Any] = None,
        company_info: Dict[str, str] = None,
        vendor_options_file: str = None,
        contacts_file: str = None
) -> Tuple[int, int]:
    """
    Process the queue and send emails to vendors.

    Args:
        queue_file: Path to the queue CSV file (uses config if None)
        vendor_file: Path to the vendor JSON file (uses config if None)
        template_path: Path to the email template (uses config if None)
        exchange_settings: Exchange settings (uses config if None)
        company_info: Company information (uses config if None)
        vendor_options_file: Path to the vendor options YAML file (uses config if None)
        contacts_file: Path to the contacts CSV file (uses default if None)

    Returns:
        Tuple containing number of successful emails and total emails
    """
    # Use config values if parameters are not provided
    queue_file = queue_file or Paths.QUEUE_PATH
    vendor_file = vendor_file or Paths.VENDOR_FILE
    template_path = template_path or Paths.EMAIL_TEMPLATE_PATH
    exchange_settings = exchange_settings or ExchangeConfig.get_settings()
    company_info = company_info or CompanyInfo.get_info()
    vendor_options_file = vendor_options_file or Paths.VENDOR_OPTIONS_FILE
    contacts_file = contacts_file or "docs/OS/contacts.csv"
    
    # Load queue data
    queue = pd.read_csv(queue_file)

    # Create vendor manager
    vendor_manager = VendorManager(
        vendor_file=vendor_file,
        vendor_options_file=vendor_options_file if os.path.exists(vendor_options_file) else None,
        contacts_file=contacts_file
    )
```

### Streamlit Application Updates

The "Send RFQ Emails" page in `streamlit_app/pages/05_send_rfq_emails.py` was updated to use contacts from CSV:

```python
# Load vendors and contacts from CSV
contacts_file = str(parent_dir / "docs" / "OS" / "contacts.csv")
vendors_data = load_vendors(vendor_file, contacts_file)
```

And for processing the entire queue:

```python
# Process the entire queue
contacts_file = str(parent_dir / "docs" / "OS" / "contacts.csv")
results = process_queue_and_send_emails(
    queue_file=str(Paths.QUEUE_PATH),
    vendor_file=vendor_file,
    template_path=template_path,
    exchange_settings=ExchangeConfig.get_settings(),
    company_info=company_info,
    contacts_file=contacts_file
)
```

## Benefits of Using Contacts CSV

1. **Centralized Contact Management**: All vendor contacts are now managed in a single CSV file, making it easier to update and maintain.
2. **Improved Data Organization**: The CSV format provides a clear structure for contact information with separate fields for first name, last name, email, etc.
3. **Backward Compatibility**: The implementation maintains backward compatibility by falling back to JSON contacts if CSV contacts are not found.
4. **Simplified Updates**: Non-technical users can easily update contact information using Excel or other spreadsheet software.

## Testing

The changes were tested by:

1. Verifying that contacts are correctly loaded from the CSV file
2. Confirming that the primary contact is correctly identified
3. Testing the fallback to JSON contacts when CSV contacts are not available
4. Ensuring that emails are sent to the correct contacts

## Conclusion

The RFQ Sender application now uses contact information from the `docs/OS/contacts.csv` file while maintaining backward compatibility with the existing JSON-based contact system. This change improves the maintainability of the application and makes it easier for users to update contact information.