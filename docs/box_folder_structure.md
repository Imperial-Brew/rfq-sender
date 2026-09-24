# docs/box_hybrid_structure.md - Box Hybrid Folder Structure Implementation

This document describes the implementation of the hybrid folder structure for RFQ documentation in Box, as outlined in `.junie/box_structure.md`.

## Overview

The hybrid folder structure organizes RFQ documentation first by quote/order number, then by part number, with vendor-specific folders generated in a subfolder and shared via Box links. This structure supports automation, easy auditing, and minimal duplication of files.

## Folder Structure

```
/Box/FinishingRFQs/QT57267/
├── PN-001/
├── PN-002/
├── PN-003/
├── PN-004/
├── PN-005/
└── vendor_links/
    ├── HeatTreatCo/
    ├── AnodizePro/
    └── NickelWorks/
```

## Implementation

The hybrid folder structure is implemented in the following files:

- `scripts/box/box_integration.py`: Contains the `BoxIntegration` class with methods for creating the hybrid folder structure
- `utils/box_helpers.py`: `upload_and_share_for_part()` creates the quote/part folders, uploads files and creates the share link; the web app calls it from `POST /api/send-rfq/box/{part_number}`
- `scripts/box/test_hybrid_structure.py`: A test script for verifying the hybrid folder structure

### BoxIntegration Class

The `BoxIntegration` class has been extended with the following methods:

#### create_rfq_structure

```python
def create_rfq_structure(self, quote_id: str, part_numbers: List[str], vendors: List[str]) -> Dict[str, Any]:
    """
    Create the hybrid folder structure for an RFQ as described in box_structure.md.
    
    Args:
        quote_id: The quote or order number (e.g., QT57267)
        part_numbers: List of part numbers to create folders for
        vendors: List of vendor names to create folders for
        
    Returns:
        Dictionary containing folder objects and IDs
    """
```

This method creates the master RFQ folder, part folders, vendor_links folder, and vendor folders. It returns a dictionary containing all the folder objects.

#### upload_part_files

```python
def upload_part_files(self, part_number: str, files: List[str], part_folder: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Upload files for a specific part to its folder.
    
    Args:
        part_number: The part number
        files: List of file paths for this part
        part_folder: The part folder object
        
    Returns:
        List of uploaded file objects
    """
```

This method uploads files for a specific part to its folder.

#### link_files_to_vendor

```python
def link_files_to_vendor(self, vendor: str, part_numbers: List[str], 
                       part_folders: Dict[str, Dict[str, Any]], 
                       vendor_folder: Dict[str, Any]) -> bool:
    """
    Create links to part files in vendor folder.
    
    Args:
        vendor: Vendor name
        part_numbers: List of part numbers this vendor is quoting
        part_folders: Dictionary of part folders
        vendor_folder: The vendor folder object
        
    Returns:
        True if successful, False otherwise
    """
```

This method creates links to part files in the vendor folder, allowing vendors to access only the files relevant to them.

### Web app integration

`upload_and_share_for_part()` in `utils/box_helpers.py`:

1. Creates (or finds) the quote folder and part folder using `create_rfq_structure`
2. Uploads the part's files using `upload_part_files`
3. Creates the share link, password-protected for CUI/ITAR parts

Vendor sub-folders and `link_files_to_vendor` exist in `BoxIntegration` but are not
used by the web app today; every vendor gets the part folder's share link.

## Testing

The `test_hybrid_structure.py` script can be used to test the hybrid folder structure implementation. It:

1. Creates test files for each part number
2. Creates the hybrid folder structure
3. Uploads files to part folders
4. Links files to vendor folders
5. Creates share links for vendor folders

Run the test script with:

```
python scripts\box\test_hybrid_structure.py
```

## Usage

When sending RFQ emails, the system will automatically:

1. Create a master folder named with the quote ID
2. Create part folders for each part number
3. Upload files to the appropriate part folders
4. Create a vendor_links folder
5. Create a vendor folder for the recipient
6. Link relevant files to the vendor folder
7. Create a share link for the vendor folder
8. Include the share link in the email

This ensures that vendors only see the files relevant to them, while maintaining a clean and organized structure for internal use.