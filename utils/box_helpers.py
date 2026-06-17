import random
import string
import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

def detect_cui_itar(row_series) -> bool:
    """
    Detect if a queue item contains CUI/ITAR controlled information.
    Checks the 'cui_itar' column in the row series.
    """
    val = row_series.get("cui_itar", "")
    if isinstance(val, bool):
        return val
    s = str(val).strip().upper()
    return s in ("TRUE", "YES", "Y", "1")

def generate_password(length: int = 12) -> str:
    """
    Generate a random alphanumeric password for Box share links.
    """
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))

def get_rfq_files(file_location: str, part_number: str) -> List[str]:
    """
    Scan file_location for files matching part_number.
    Skips common non-drawing files (.xls, .doc, etc).
    """
    if not file_location or not os.path.exists(file_location):
        return []
    
    files = []
    part_number = str(part_number).strip()
    
    # Simple glob match for the part number
    search_pattern = os.path.join(file_location, f"*{part_number}*")
    candidates = glob.glob(search_pattern, recursive=True)
    
    skip_exts = {'.xls', '.xlsx', '.doc', '.docx', '.csv', '.txt'}
    
    for c in candidates:
        if os.path.isfile(c):
            ext = os.path.splitext(c)[1].lower()
            if ext not in skip_exts:
                files.append(c)
    
    return files

def persist_box_update(
    df: pd.DataFrame, 
    row_idx: int,
    share_link: str = "",
    password: str = "",
    unshared_at: str = "",
    files_uploaded: int = 0,
    part_folder: Dict[str, Any] = None,
    quote_folder: Dict[str, Any] = None,
    box: Any = None
):
    """
    Update the queue DataFrame with Box metadata.
    Does NOT call save_queue (caller should do that).
    """
    if share_link:
        df.loc[row_idx, 'box_share_link'] = share_link
    if password:
        df.loc[row_idx, 'box_password'] = password
    
    # These might not exist in all schemas but we try to set them
    if 'box_part_folder_id' in df.columns and part_folder:
        df.loc[row_idx, 'box_part_folder_id'] = part_folder.get('id', '')
    if 'box_quote_folder_id' in df.columns and quote_folder:
        df.loc[row_idx, 'box_quote_folder_id'] = quote_folder.get('id', '')

def upload_and_share_for_part(
    box: Any,
    row: pd.Series,
    attachments: List[str],
    access: str = "open"
) -> Dict[str, Any]:
    """
    High-level helper to create/find an RFQ folder structure,
    upload files, and create a share link.
    """
    part_number = str(row.get("part_number", "")).strip()
    quote_id = str(row.get("qt_so_number", "")).strip() or "UNKNOWN_QUOTE"
    
    if not part_number:
        return {"error": "No part number found in row."}

    try:
        # 1. Create structure
        # Use existing BoxIntegration method if it matches, otherwise simulate
        # box_integration.py has create_rfq_structure(quote_id, part_numbers, vendors)
        # But we only have one part here.
        
        # For simplicity in this helper, we'll use the core methods of BoxIntegration
        structure = box.create_rfq_structure(
            quote_id=quote_id,
            part_numbers=[part_number],
            vendors=[] # We don't necessarily know vendors yet here
        )
        
        part_folder = structure.get("part_folders", {}).get(part_number)
        quote_folder = structure.get("quote_folder")
        
        if not part_folder:
            return {"error": f"Could not create/find Box folder for part {part_number}"}
            
        # 2. Upload files
        files_uploaded = 0
        if attachments:
            uploaded = box.upload_part_files(part_number, attachments, part_folder)
            files_uploaded = len(uploaded)
            
        # 3. Create share link
        # ITAR/CUI check
        is_cui = detect_cui_itar(row)
        password = None
        if is_cui:
            password = generate_password()
            
        share_link = box.create_share_link(
            folder=part_folder,
            access=access,
            password=password,
            expire_days=30
        )
        
        return {
            "share_link": share_link,
            "password": password,
            "is_cui": is_cui,
            "files_uploaded": files_uploaded,
            "part_folder": part_folder,
            "quote_folder": quote_folder
        }
        
    except Exception as e:
        return {"error": str(e)}
