import streamlit as st
import pandas as pd
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import yaml
import jinja2
from datetime import datetime

# Add parent directory to path to import from other modules
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import configuration and utility functions
from core.config import Paths, CompanyInfo, LoggingConfig, init_config
from core.secrets import get_section
from core.email.email_manager import EmailManager
from core.vendors.vendor_manager import VendorManager
from streamlit_app.utils.auth_shim import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication
from scripts.utils.spec_check import SpecProcessValidator
from scripts.box.box_integration import BoxIntegration
import secrets
import string

# Check authentication
if not require_authentication():
    st.stop()

# Initialize configuration
init_config()

# Set up logging
logger = LoggingConfig.setup_logging(__name__, "send_rfq_emails.log")

def normalize_process_spec(text: str, validator: SpecProcessValidator = None) -> str:
    """
    Normalize a process or spec name using the SpecProcessValidator.

    Args:
        text: The process or spec name to normalize
        validator: Optional SpecProcessValidator instance. If None, a new one will be created.

    Returns:
        The normalized process or spec name
    """
    if not text:
        return ""

    # Create a validator if one wasn't provided
    if validator is None:
        validator = SpecProcessValidator()

    # Use the validator's normalize method
    return validator.normalize(text)

def load_data(queue_file: str, contacts_file: str, vendor_options_file: str, 
              logger: logging.Logger = None) -> Tuple[pd.DataFrame, Dict[Any, Dict[str, Any]]]:
    """
    Load data from CSV and YAML files and prepare vendor information.

    Args:
        queue_file: Path to the queue CSV file (Queue.csv)
        contacts_file: Path to the contacts CSV file (contacts.csv)
        vendor_options_file: Path to the vendor options YAML file (vendor_options.yaml)
        logger: Optional logger for logging messages

    Returns:
        Tuple containing:
            - DataFrame with queue data (with renamed columns)
            - Dictionary mapping vendor_id to vendor information (email and name)
    """
    if logger:
        logger.info(f"Loading queue data from {queue_file}")
    else:
        print(f"Loading queue data from {queue_file}")

    if not os.path.exists(queue_file):
        if logger:
            logger.error(f"Queue file not found: {queue_file}")
        else:
            print(f"Queue file not found: {queue_file}")
        raise FileNotFoundError(f"Queue file not found: {queue_file}")

    if logger:
        logger.info(f"Loading contacts data from {contacts_file}")
    else:
        print(f"Loading contacts data from {contacts_file}")

    if not os.path.exists(contacts_file):
        if logger:
            logger.error(f"Contacts file not found: {contacts_file}")
        else:
            print(f"Contacts file not found: {contacts_file}")
        raise FileNotFoundError(f"Contacts file not found: {contacts_file}")

    if logger:
        logger.info(f"Loading vendor options from {vendor_options_file}")
    else:
        print(f"Loading vendor options from {vendor_options_file}")

    if not os.path.exists(vendor_options_file):
        if logger:
            logger.error(f"Vendor options file not found: {vendor_options_file}")
        else:
            print(f"Vendor options file not found: {vendor_options_file}")
        raise FileNotFoundError(f"Vendor options file not found: {vendor_options_file}")

    try:
        # Load queue data with UTF-8 encoding and error handling
        try:
            queue = pd.read_csv(queue_file, encoding='utf-8')
        except UnicodeDecodeError:
            # Fall back to cp1252 if UTF-8 fails
            queue = pd.read_csv(queue_file, encoding='cp1252')

        # Log the number of items where SENT=YES, but don't filter them out
        if 'SENT' in queue.columns:
            sent_items_count = len(queue[queue['SENT'] == 'YES'])
            if logger:
                logger.info(f"Found {sent_items_count} items where SENT=YES. Total items: {len(queue)}")
            else:
                print(f"Found {sent_items_count} items where SENT=YES. Total items: {len(queue)}")

        # Load contacts data with UTF-8 encoding and error handling
        try:
            contacts = pd.read_csv(contacts_file, encoding='utf-8')
        except UnicodeDecodeError:
            # Fall back to cp1252 if UTF-8 fails
            contacts = pd.read_csv(contacts_file, encoding='cp1252')

        # Load vendor options data
        with open(vendor_options_file, 'r', encoding='utf-8') as f:
            vendor_options = yaml.safe_load(f)

        # Rename queue columns to match expected names
        queue_column_mapping = {
            'RFQ #': 'RFQ #',
            'Part_Number': 'part_number',
            'Rev': 'Rev',
            'Print Callout': 'callout',
            'process': 'process',
            'spec': 'spec',
            'material': 'material',
            'quantities': 'quantities',
            'file_location': 'file_location',
            'submitted_by': 'submitted_by',
            'qt/so #': 'qt/so #'
        }
        
        # Rename columns
        queue = queue.rename(columns=queue_column_mapping)
        
        # Add part_number as quote_id since it doesn't exist in the queue.csv
        queue['quote_id'] = queue['part_number']

        # Process contacts data
        # Filter to primary contacts only
        # The 'Primary' value is in the 9th column which might be unnamed in the CSV
        # Find the column that contains 'Primary' values
        primary_column = None
        for col in contacts.columns:
            if 'Primary' in contacts[col].values:
                primary_column = col
                break

        # Filter to primary contacts in the finishing category
        if primary_column:
            primary_contacts = contacts[(contacts['type'] == 'finishing') & (contacts[primary_column] == 'Primary')]
        else:
            # Fallback to just filtering by type if we can't find the primary column
            primary_contacts = contacts[contacts['type'] == 'finishing']

        # Create vendor info dictionary
        vendor_info = {}
        for _, row in primary_contacts.iterrows():
            vendor_id = row['Vendor'].strip()
            email = row['Email'].strip() if pd.notna(row['Email']) else ""

            # Skip entries without email
            if not email:
                continue

            # Get the first name if available
            first_name = row['First'].strip() if pd.notna(row['First']) else ""

            vendor_info[vendor_id] = {
                'email': email,
                'vendor_name': vendor_id,  # Use vendor name as is
                'first_name': first_name  # Add first name for personalized greeting
            }

        # Enrich vendor info with capabilities from vendor_options
        if vendor_options and 'vendors' in vendor_options:
            for vendor in vendor_options['vendors']:
                vendor_name = vendor['name']
                if vendor_name in vendor_info:
                    # Add capabilities information
                    if 'processes' in vendor:
                        # Store the full process objects, ensuring it's not None
                        vendor_info[vendor_name]['processes'] = vendor['processes'] if vendor['processes'] is not None else []

    except Exception as e:
        if logger:
            logger.error(f"Error loading files: {str(e)}")
        else:
            print(f"Error loading files: {str(e)}")
        raise

    return queue, vendor_info

def detect_cui_itar(row: pd.Series) -> bool:
    """
    Prefer explicit cui_itar column if present; otherwise fall back to heuristic
    scanning of spec/process/callout/material for 'CUI' or 'ITAR'.
    """
    try:
        flag = row.get('cui_itar', None)
        if isinstance(flag, str):
            s = flag.strip().upper()
            if s in ("TRUE", "YES", "Y", "1"):  # treat any truthy token as True
                return True
            if s in ("FALSE", "NO", "N", "0"):  # explicit false
                return False
        elif isinstance(flag, bool):
            return bool(flag)
    except Exception:
        pass

    fields_to_scan = [
        str(row.get('spec', '')),
        str(row.get('process', '')),
        str(row.get('callout', '')),
        str(row.get('material', '')),
    ]
    text = " ".join(fields_to_scan).upper()
    return ("CUI" in text) or ("ITAR" in text)


def generate_password(length: int = 14) -> str:
    """Generate a random, email-friendly password."""
    alphabet = string.ascii_letters + string.digits + "-_@#"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_rfq_part_folder(box: "BoxIntegration", qt_so: str, part_number: str):
    """
    Ensure Box folders exist for 'RFQs/[qt/so #]/[Part_Number]'.
    Returns (rfqs_root, quote_folder, part_folder) or (None, None, None) on failure.
    """
    rfqs_root = box.create_folder("RFQs", parent_folder_id="0")
    if not rfqs_root:
        return None, None, None

    quote_name = str(qt_so).strip() if qt_so else str(part_number).strip()
    quote_folder = box.create_folder(quote_name, parent_folder_id=rfqs_root.id)
    if not quote_folder:
        return rfqs_root, None, None

    part_folder = box.create_folder(str(part_number).strip(), parent_folder_id=quote_folder.id)
    if not part_folder:
        return rfqs_root, quote_folder, None

    return rfqs_root, quote_folder, part_folder


def upload_and_share_for_part(
    box: "BoxIntegration",
    row: pd.Series,
    attachments: List[str],
    access: str = "open",          # Consider "company" for internal-only links
    default_expire_days: int = 30,
):
    """
    - Creates RFQs/[qt/so #]/[Part_Number]
    - Uploads attachments to the part folder
    - Detects CUI/ITAR to optionally add password protection
    - Returns a dict with: share_link, password, is_cui, part_folder, quote_folder, rfqs_root,
      files_uploaded, file_manifest, unshared_at
    """
    qt_so = row.get("qt/so #", "")
    part_number = row.get("part_number", "")
    if not part_number:
        return {"error": "Missing part_number"}

    rfqs_root, quote_folder, part_folder = ensure_rfq_part_folder(box, qt_so, part_number)
    if not part_folder:
        return {"error": f"Failed to prepare Box folder for {part_number}"}

    # Upload files first (if present)
    files_uploaded = 0
    manifest = []
    if attachments:
        box.upload_files(attachments, part_folder)
        files_uploaded = len(attachments)
        manifest = [os.path.basename(p) for p in attachments]

    # Decide protection
    is_cui = detect_cui_itar(row)
    password = generate_password() if is_cui else None

    # Compute expiration timestamp for recording (Box returns link; we record intended expiry)
    unshared_at = None
    if default_expire_days and default_expire_days > 0:
        from datetime import timedelta
        unshared_at = (datetime.now() + timedelta(days=default_expire_days)).isoformat()

    share_link = box.create_share_link(
        part_folder,
        access=access,
        password=password,
        expire_days=default_expire_days,
    )

    return {
        "share_link": share_link,
        "password": password,
        "is_cui": is_cui,
        "part_folder": part_folder,
        "quote_folder": quote_folder,
        "rfqs_root": rfqs_root,
        "files_uploaded": files_uploaded,
        "file_manifest": ";".join(manifest) if manifest else "",
        "box_access": access,
        "unshared_at": unshared_at,
    }


def inject_box_link_into_body(html_body: str, share_link: str, is_cui: bool) -> str:
    """Append a styled Box link section to the existing HTML email body."""
    if not share_link:
        return html_body

    banner = f"""
    <div style="margin-top:16px;padding:14px;border:1px solid #d0d7de;border-radius:8px;background:#f6f8fa;">
      <div style="font-size:16px;font-weight:600;margin-bottom:6px;">
        RFQ Files in Box { '(Password Protected)' if is_cui else '' }
      </div>
      <div>
        <a href="{share_link}" style="display:inline-block;padding:10px 14px;background:#2d7ff9;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;">
          Open RFQ Folder
        </a>
      </div>
      <div style="margin-top:8px;color:#57606a;font-size:13px;">
        If you have trouble opening the link, copy and paste this URL into your browser:<br/>
        <code style="font-size:12px;">{share_link}</code>
      </div>
    </div>
    """
    if "</body>" in html_body:
        return html_body.replace("</body>", banner + "\n</body>")
    if "</html>" in html_body:
        return html_body.replace("</html>", banner + "\n</html>")
    return html_body + banner

def find_vendors_for_process_spec(vendor_info: Dict[str, Dict[str, Any]], 
                                 process: str, 
                                 spec: str = None,
                                 validator: SpecProcessValidator = None) -> List[Dict[str, Any]]:
    """
    Find vendors that can handle a specific process and optionally a spec.
    
    Args:
        vendor_info: Dictionary mapping vendor_id to vendor information
        process: Process name to match
        spec: Optional spec name to match
        validator: Optional SpecProcessValidator instance
        
    Returns:
        List of vendor dictionaries that can handle the process/spec
    """
    if validator is None:
        validator = SpecProcessValidator()
    
    # Normalize process and spec for comparison
    normalized_process = normalize_process_spec(process, validator)
    normalized_spec = normalize_process_spec(spec, validator) if spec else None
    
    matching_vendors = []
    
    process_only_vendors = []
    for vendor_id, vendor_data in vendor_info.items():
        if 'processes' not in vendor_data:
            continue
        
        can_handle_process = False
        can_handle_spec = normalized_spec is None  # If no spec is provided, default to True
        
        for vendor_process in vendor_data['processes']:
            if not vendor_process or 'name' not in vendor_process:
                continue
            vendor_process_name = normalize_process_spec(vendor_process['name'], validator)
            if vendor_process_name == normalized_process:
                can_handle_process = True
                # If spec is provided, check if vendor can handle it
                if normalized_spec and 'specs' in vendor_process and vendor_process['specs']:
                    for vendor_spec in vendor_process['specs']:
                        if not vendor_spec:
                            continue
                        if isinstance(vendor_spec, dict):
                            raw_spec = vendor_spec.get('number') or vendor_spec.get('name') or ''
                        else:
                            raw_spec = vendor_spec
                        vendor_spec_name = normalize_process_spec(raw_spec, validator)
                        if vendor_spec_name == normalized_spec:
                            can_handle_spec = True
                            break
                # If we found a match for both process and spec (or no spec was required), stop checking
                if can_handle_process and can_handle_spec:
                    break
        
        # Track process-capable vendors for fallback
        if can_handle_process and not process_only_vendors:
            # we will fill later after loop to avoid repeated copies
            pass
        
        if can_handle_process and can_handle_spec:
            vendor_copy = vendor_data.copy()
            vendor_copy['id'] = vendor_id
            matching_vendors.append(vendor_copy)
        elif can_handle_process and normalized_spec is not None:
            # remember for fallback when spec provided but no matches
            vendor_copy = vendor_data.copy()
            vendor_copy['id'] = vendor_id
            process_only_vendors.append(vendor_copy)
    
    # Fallback: if spec given but no exact spec matches, return process-only vendors
    if normalized_spec is not None and not matching_vendors and process_only_vendors:
        return process_only_vendors
    
    return matching_vendors


def create_email_body(queue_items: pd.DataFrame, 
                     vendor_name: str, 
                     contact_name: str = None,
                     company_info: Dict[str, str] = None) -> str:
    """
    Create HTML email body for RFQ using Jinja2 templates.
    
    Args:
        queue_items: DataFrame containing queue items for this vendor
        vendor_name: Name of the vendor
        contact_name: Optional contact first name for personalized greeting
        company_info: Dictionary with company information
        
    Returns:
        HTML formatted email body
    """
    # Default company info if not provided
    if company_info is None:
        company_info = {
            'name': CompanyInfo.get_name(),
            'sender_name': CompanyInfo.get_sender_name(),
            'sender_title': CompanyInfo.get_sender_title(),
            'sender_phone': CompanyInfo.get_sender_phone(),
            'sender_email': CompanyInfo.get_sender_email()
        }
    
    # Create a Jinja2 environment
    template_dir = os.path.join(parent_dir, 'config', 'templates')
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        autoescape=jinja2.select_autoescape(['html', 'xml'])
    )
    
    # Try to load the template
    try:
        template = env.get_template('rfq_email.html')
    except jinja2.exceptions.TemplateNotFound:
        # Fallback to a basic template if the file doesn't exist
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            {% if contact_name %}
            <p>Hello {{ contact_name }},</p>
            {% else %}
            <p>Hello,</p>
            {% endif %}
            
            <p>We would like to request a quote for the following part(s):</p>
            
            <table>
                <tr>
                    <th>Part Number</th>
                    <th>Process</th>
                    <th>Spec</th>
                    <th>Quantities</th>
                </tr>
                {% for item in items %}
                <tr>
                    <td>{{ item.part_number }}</td>
                    <td>{{ item.process }}</td>
                    <td>{{ item.spec }}</td>
                    <td>{{ item.quantities }}</td>
                </tr>
                {% endfor %}
            </table>
            
            <p>Please provide your best pricing and lead time.</p>
            
            <p>Thank you,</p>
            <p>{{ sender_name }}<br>
            {{ sender_title }}<br>
            {{ company_name }}<br>
            {{ sender_phone }}<br>
            {{ sender_email }}</p>
        </body>
        </html>
        """
        template = jinja2.Template(template_str)
    
    # Prepare items for the template
    items = []
    for _, row in queue_items.iterrows():
        item = {
            'part_number': row.get('part_number', ''),
            'process': row.get('process', ''),
            'spec': row.get('spec', ''),
            'quantities': row.get('quantities', '')
        }
        items.append(item)
    
    # Render the template
    html_content = template.render(
        items=items,
        contact_name=contact_name,
        vendor_name=vendor_name,
        company_name=company_info.get('name', ''),
        sender_name=company_info.get('sender_name', ''),
        sender_title=company_info.get('sender_title', ''),
        sender_phone=company_info.get('sender_phone', ''),
        sender_email=company_info.get('sender_email', '')
    )
    
    return html_content


def create_draft_email(recipient: str, 
                      subject: str, 
                      body: str, 
                      attachments: List[str] = None,
                      cc: List[str] = None,
                      exchange_settings: Dict[str, Any] = None) -> bool:
    """
    Create a draft email using Microsoft Graph (no EWS).
    """
    try:
        # Graph-only: pull user UPN/CC from secrets
        ex_cfg = get_section("exchange")
        mgr = EmailManager(exchange_settings={"cc": ex_cfg.get("cc")})
        return mgr.create_draft_email(
            recipient=recipient,
            subject=subject,
            body=body,
            attachments=attachments,
            cc_email=(cc[0] if isinstance(cc, list) and cc else ex_cfg.get("cc")),
            html_format=True,
        )
    except Exception as e:
        logger.error(f"Error creating draft email (Graph): {str(e)}")
        return False


def get_file_attachments(file_path: str, logger: logging.Logger = None) -> List[str]:
    """
    Get file attachments from a file path, handling both direct files and directories.
    
    Args:
        file_path: Path to file or directory
        logger: Optional logger for logging messages
        
    Returns:
        List of file paths to attach
    """
    attachments = []
    
    if not file_path or not os.path.exists(file_path):
        if logger:
            logger.warning(f"File path does not exist: {file_path}")
        return attachments
    
    # If it's a directory, get all files in it
    if os.path.isdir(file_path):
        for root, _, files in os.walk(file_path):
            for file in files:
                # Skip hidden files and temp files
                if file.startswith('.') or file.startswith('~$'):
                    continue
                attachments.append(os.path.join(root, file))
    else:
        # It's a single file
        attachments.append(file_path)
    
    return attachments


def setup_page():
    """Configure the page settings."""
    st.title("Send RFQ Emails")
    st.markdown("""
    This page allows you to create RFQ email drafts in Outlook for vendors based on parts in the queue.
    Vendors are automatically matched based on their process and spec capabilities.
    
    > **Note:** This tool creates draft emails in your Outlook client. No emails are sent automatically.
    > You will need to review and manually send each draft from Outlook.
    """)


def display_queue_for_emails(user: Dict[str, Any], role: str):
    """
    Display the queue with options to send emails.
    
    Args:
        user: User information dictionary
        role: User role (admin, editor, viewer)
    """
    try:
        # Load queue data using centralized path configuration
        queue_file = str(Paths.QUEUE_PATH)
        contacts_file = str(parent_dir / "docs" / "OS" / "contacts.csv")
        # Use the centralized path configuration for vendor_options.yaml
        # This ensures consistent path handling across the application
        vendor_options_file = str(Paths.VENDOR_OPTIONS_FILE)
        
        try:
            # Use load_data function
            queue, vendor_info = load_data(queue_file, contacts_file, vendor_options_file, logger)
            
            if queue.empty:
                st.info("The queue is currently empty. Add parts using the 'Add to Queue' page.")
                return
            
            # Display the queue
            st.subheader("RFQ Queue")
            
            # Format the dataframe for display
            display_df = queue.copy()
            
            # Convert date columns to datetime if they exist
            if "due_date" in display_df.columns:
                display_df["due_date"] = pd.to_datetime(display_df["due_date"], errors="coerce")
                # Store datetime objects for comparison
                display_df["due_date_dt"] = display_df["due_date"]
            
            # Add a status column based on due date if it exists
            if "due_date_dt" in display_df.columns:
                today = datetime.now().date()
                
                # Define a safe date comparison function
                def safe_date_compare(x):
                    try:
                        # Handle NaN, NaT, None, or any non-datetime value
                        if pd.isna(x) or x is pd.NaT or x is None:
                            return "No Date"
                        
                        # Convert to datetime if it's a string
                        if isinstance(x, str):
                            try:
                                date_val = pd.to_datetime(x).date()
                            except:
                                return "No Date"
                        # Ensure x is a datetime object
                        elif not isinstance(x, (pd.Timestamp, datetime)):
                            return "No Date"
                        else:
                            date_val = x.date() if hasattr(x, 'date') else None
                        
                        if date_val is None:
                            return "No Date"
                            
                        # Ensure both values are of the same type before comparison
                        if not isinstance(date_val, type(today)):
                            # Convert date_val to the same type as today if possible
                            try:
                                date_val = type(today)(date_val)
                            except:
                                return "No Date"
                        
                        return "Overdue" if date_val < today else "Active"
                    except Exception as e:
                        logger.debug(f"Error comparing date value {x} of type {type(x)}: {str(e)}")
                        return "No Date"
                
                # Apply the safe comparison function
                display_df["status"] = display_df["due_date_dt"].apply(safe_date_compare)
                
                # Format dates for display after comparison is done
                if "due_date" in display_df.columns:
                    display_df["due_date"] = display_df["due_date"].dt.strftime("%Y-%m-%d")
            
            # Highlight expedited items
            if "expedited" in display_df.columns:
                display_df["priority"] = display_df["expedited"].apply(
                    lambda x: "⚠️ Expedited" if x else "Standard"
                )
            
            # Reorder and select columns for display
            columns_to_display = ["part_number", "process", "spec", "quantities"]
            if "priority" in display_df.columns:
                columns_to_display.append("priority")
            if "due_date" in display_df.columns:
                columns_to_display.append("due_date")
            if "status" in display_df.columns:
                columns_to_display.append("status")
            
            # Only include columns that actually exist in the dataframe
            columns_to_display = [col for col in columns_to_display if col in display_df.columns]
            
            # Add a selection column
            display_df_with_selection = display_df.copy()
            
            # Display the dataframe with selection
            selected_indices = st.multiselect(
                "Select parts to send RFQ emails for:",
                options=list(range(len(display_df_with_selection))),
                format_func=lambda i: f"{display_df_with_selection.iloc[i]['part_number']} - {display_df_with_selection.iloc[i]['process']}"
            )
            
            if selected_indices:
                selected_parts = display_df_with_selection.iloc[selected_indices]
                st.write("Selected parts:")
                st.dataframe(
                    selected_parts[columns_to_display],
                    use_container_width=True,
                    hide_index=True
                )

            # New: Create/Update Box for selected parts
            if st.button("Create/Update Box Folders/Links for Selected Parts", disabled=len(selected_indices) == 0):
                try:
                    with st.spinner("Creating Box folders, uploading files, and updating CSV..."):
                        # Initialize Box
                        box = BoxIntegration(logger=logger)
                        if not box or not box.client:
                            # Surface diagnostics to help user resolve missing config
                            diag = {}
                            try:
                                if box and hasattr(box, "diagnostics"):
                                    diag = box.diagnostics()
                                elif box:
                                    diag = {
                                        "tried_paths": getattr(box, "tried_paths", []),
                                        "config_path": getattr(box, "config_path", None),
                                        "last_error": getattr(box, "last_error", ""),
                                        "client_initialized": bool(getattr(box, "client", None)),
                                    }
                            except Exception as _e:
                                diag = {"client_initialized": False, "last_error": str(_e)}
                            st.error("Box initialization failed. Provide [box].jwt_json in Streamlit Secrets or set BOX_CONFIG_PATH to your 0__config.json. See diagnostics below.")
                            st.write({
                                "config_path": diag.get("config_path"),
                                "tried_paths": diag.get("tried_paths"),
                                "client_initialized": diag.get("client_initialized"),
                                "last_error": diag.get("last_error"),
                                "BOX_JWT_JSON_present": bool(os.environ.get("BOX_JWT_JSON", "")),
                            })
                            return

                        # Work on a slice so we can map back by index
                        selected_parts_df = queue.iloc[selected_indices]
                        box_results = []

                        for idx, row in selected_parts_df.iterrows():
                            part_number = row.get("part_number", "")
                            # Collect local files
                            attachments = []
                            if 'file_location' in row and row['file_location']:
                                attachments = get_file_attachments(row['file_location'], logger)

                            # Upload to Box and create share link
                            upload_result = upload_and_share_for_part(
                                box=box,
                                row=row,
                                attachments=attachments,
                                access="company",
                                default_expire_days=30,
                            )

                            if upload_result.get("error"):
                                logger.warning(upload_result["error"])
                                box_results.append({
                                    "part_number": part_number,
                                    "status": "Error",
                                    "detail": upload_result.get("error"),
                                })
                                continue

                            # Persist to queue DataFrame
                            queue.loc[idx, 'box_rfq_root_id'] = getattr(upload_result.get('rfqs_root'), 'id', '')
                            queue.loc[idx, 'box_quote_folder_id'] = getattr(upload_result.get('quote_folder'), 'id', '')
                            queue.loc[idx, 'box_part_folder_id'] = getattr(upload_result.get('part_folder'), 'id', '')
                            queue.loc[idx, 'box_share_link'] = upload_result.get('share_link', '') or ''
                            queue.loc[idx, 'box_access'] = upload_result.get('box_access', '')
                            queue.loc[idx, 'box_password'] = upload_result.get('password', '') or ''
                            queue.loc[idx, 'box_unshared_at'] = upload_result.get('unshared_at', '') or ''
                            queue.loc[idx, 'box_last_updated'] = datetime.now().isoformat()
                            queue.loc[idx, 'files_uploaded'] = upload_result.get('files_uploaded', 0)
                            queue.loc[idx, 'file_manifest'] = upload_result.get('file_manifest', '')

                            box_results.append({
                                "part_number": part_number,
                                "status": "Updated",
                                "box_part_folder_id": queue.loc[idx, 'box_part_folder_id'],
                                "share_link": queue.loc[idx, 'box_share_link'],
                            })

                        # Save CSV
                        queue.to_csv(queue_file, index=False)
                        results_df = pd.DataFrame(box_results)
                        st.success(f"Updated Box info for {len(results_df)} selected part(s).")
                        st.dataframe(results_df, use_container_width=True, hide_index=True)
                        logger.info(f"Box folders/links updated for {len(results_df)} selected parts")
                except Exception as e:
                    st.error(f"Error creating Box folders or updating CSV: {str(e)}")
                    logger.error(f"Error creating Box folders or updating CSV: {str(e)}")
            
            # Process selected parts
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Create Draft Emails for Selected Parts", disabled=len(selected_indices) == 0):
                    if role not in ["admin", "editor"]:
                        st.warning("You need admin or editor privileges to send emails.")
                        return
                    
                    try:
                        with st.spinner("Creating draft emails..."):
                            # Get company info from CompanyInfo and override with user info
                            company_info = CompanyInfo.get_info()
                            company_info.update({
                                "sender_name": user["name"],
                                "sender_title": user.get("title", "Estimator"),
                                "sender_email": user.get("email", get_section("exchange").get("username", "")),
                                "sender_phone": user.get("phone", CompanyInfo.get_sender_phone())
                            })
                            
                            # Get exchange settings (Graph only)
                            ex_cfg = get_section("exchange")
                            exchange_settings = {
                                "username": ex_cfg.get("username", ""),
                                "cc": ex_cfg.get("cc")
                            }
                            
                            # Initialize Box (JWT)
                            box = BoxIntegration(logger=logger)
                            if not box or not box.client:
                                diag = {}
                                try:
                                    if box and hasattr(box, "diagnostics"):
                                        diag = box.diagnostics()
                                    elif box:
                                        diag = {
                                            "tried_paths": getattr(box, "tried_paths", []),
                                            "config_path": getattr(box, "config_path", None),
                                            "last_error": getattr(box, "last_error", ""),
                                            "client_initialized": bool(getattr(box, "client", None)),
                                        }
                                except Exception as _e:
                                    diag = {"client_initialized": False, "last_error": str(_e)}
                                st.error("Box initialization failed. Provide [box].jwt_json in Streamlit Secrets or set BOX_CONFIG_PATH to your 0__config.json. See diagnostics below.")
                                st.write({
                                    "config_path": diag.get("config_path"),
                                    "tried_paths": diag.get("tried_paths"),
                                    "client_initialized": diag.get("client_initialized"),
                                    "last_error": diag.get("last_error"),
                                    "BOX_JWT_JSON_present": bool(os.environ.get("BOX_JWT_JSON", "")),
                                })
                                return

                            # Process only selected parts
                            selected_parts_df = queue.iloc[selected_indices]
                            results = []
                            
                            # Create a validator instance to reuse
                            validator = SpecProcessValidator()
                            
                            for _, row in selected_parts_df.iterrows():
                                part_number = row["part_number"]
                                process = row["process"]
                                spec = row.get("spec", None)
                                
                                # Find vendors for this process and spec
                                matching_vendors = find_vendors_for_process_spec(
                                    vendor_info, 
                                    process, 
                                    spec, 
                                    validator
                                )
                                
                                if not matching_vendors:
                                    # Fallback: use VendorManager (config/vendors.json + contacts.csv)
                                    try:
                                        vm = VendorManager()
                                        vm_matches = vm.find_vendors_for_process_and_spec(process, spec)
                                        transformed = []
                                        for v in vm_matches:
                                            contact = vm.get_primary_contact(v)
                                            if contact and contact.get('email'):
                                                transformed.append({
                                                    'email': contact.get('email', ''),
                                                    'vendor_name': v.get('name', ''),
                                                    'first_name': contact.get('first_name', '') or contact.get('name', '')
                                                })
                                        matching_vendors = transformed
                                    except Exception as _e:
                                        logger.debug(f"VendorManager fallback error for {process}/{spec}: {_e}")
                                    if not matching_vendors:
                                        results.append({
                                            "part_number": part_number,
                                            "process": process,
                                            "status": "No vendors found",
                                            "emails_sent": 0
                                        })
                                        continue
                                
                                # Send emails to each vendor
                                emails_sent = 0
                                for vendor in matching_vendors:
                                    try:
                                        # Get vendor email and name
                                        vendor_email = vendor.get('email', '')
                                        vendor_name = vendor.get('vendor_name', '')
                                        contact_name = vendor.get('first_name', '')
                                        
                                        if not vendor_email:
                                            logger.warning(f"No email found for vendor: {vendor_name}")
                                            continue
                                        
                                        # Create email subject
                                        subject = f"RFQ for {part_number} - {process}"
                                        
                                        # Create email body
                                        body = create_email_body(
                                            queue_items=pd.DataFrame([row]),
                                            vendor_name=vendor_name,
                                            contact_name=contact_name,
                                            company_info=company_info
                                        )
                                        
                                        # Collect local files for Box upload
                                        attachments = []
                                        if 'file_location' in row and row['file_location']:
                                            file_path = row['file_location']
                                            attachments = get_file_attachments(file_path, logger)

                                        # Upload to Box and create share link (password if CUI/ITAR)
                                        upload_result = upload_and_share_for_part(
                                            box=box,
                                            row=row,
                                            attachments=attachments,
                                            access="company",
                                            default_expire_days=30,
                                        )

                                        if upload_result.get("error"):
                                            logger.warning(upload_result["error"]) 
                                            share_link = None
                                            is_cui = False
                                            password = None
                                        else:
                                            share_link = upload_result.get("share_link")
                                            is_cui = upload_result.get("is_cui", False)
                                            password = upload_result.get("password")

                                        # Inject Box link into the email body
                                        body_with_link = inject_box_link_into_body(body, share_link, is_cui)

                                        # Create the main draft (no attachments; link in body)
                                        if create_draft_email(
                                            recipient=vendor_email,
                                            subject=subject,
                                            body=body_with_link,
                                            attachments=None,
                                            cc=[exchange_settings.get('cc')] if exchange_settings.get('cc') else None,
                                            exchange_settings=exchange_settings
                                        ):
                                            emails_sent += 1
                                            logger.info(f"Draft email (with Box link) created for {vendor_email} for {part_number}")

                                            # If CUI/ITAR, create a second draft containing only the password
                                            if is_cui and password:
                                                pwd_subject = f"Password for RFQ Files – {part_number}"
                                                pwd_body = f"""
                                                <p>Hello {contact_name or ''},</p>
                                                <p>The RFQ files you received are password-protected.</p>
                                                <p><b>Password:</b> <code>{password}</code></p>
                                                <p>Please send this email about 10 minutes after the RFQ email.</p>
                                                """
                                                if create_draft_email(
                                                    recipient=vendor_email,
                                                    subject=pwd_subject,
                                                    body=pwd_body,
                                                    attachments=None,
                                                    cc=[exchange_settings.get('cc')] if exchange_settings.get('cc') else None,
                                                    exchange_settings=exchange_settings
                                                ):
                                                    logger.info(f"Password draft created for {vendor_email} for {part_number}")
                                                else:
                                                    logger.warning(f"Failed to create password draft for {vendor_email} for {part_number}")
                                        else:
                                            logger.warning(f"Failed to create draft email for {vendor_email} for {part_number}")
                                    except Exception as e:
                                        logger.error(f"Error creating draft email for {vendor.get('vendor_name', 'Unknown')} for {part_number}: {str(e)}")
                                
                                results.append({
                                    "part_number": part_number,
                                    "process": process,
                                    "status": "Success" if emails_sent > 0 else "Failed",
                                    "emails_sent": emails_sent
                                })
                            
                            # Display results
                            results_df = pd.DataFrame(results)
                            st.success(f"Processed {len(results)} parts. Created {results_df['emails_sent'].sum()} draft emails in Outlook.")
                            st.dataframe(results_df, use_container_width=True, hide_index=True)
                            
                            # Log the action
                            logger.info(f"RFQ draft emails created by {user['name']} for {len(results)} parts")
                            
                    except Exception as e:
                        st.error(f"Error creating RFQ email drafts: {str(e)}")
                        logger.error(f"Error creating RFQ email drafts: {str(e)}")
            
            with col2:
                # New: Create/Update Box for entire queue
                if st.button("Create/Update Box for Entire Queue"):
                    try:
                        with st.spinner("Creating Box folders, uploading files, and updating CSV for entire queue..."):
                            box = BoxIntegration(logger=logger)
                            if not box or not box.client:
                                diag = {}
                                try:
                                    if box and hasattr(box, "diagnostics"):
                                        diag = box.diagnostics()
                                    elif box:
                                        diag = {
                                            "tried_paths": getattr(box, "tried_paths", []),
                                            "config_path": getattr(box, "config_path", None),
                                            "last_error": getattr(box, "last_error", ""),
                                            "client_initialized": bool(getattr(box, "client", None)),
                                        }
                                except Exception as _e:
                                    diag = {"client_initialized": False, "last_error": str(_e)}
                                st.error("Box initialization failed. Provide [box].jwt_json in Streamlit Secrets or set BOX_CONFIG_PATH to your 0__config.json. See diagnostics below.")
                                st.write({
                                    "config_path": diag.get("config_path"),
                                    "tried_paths": diag.get("tried_paths"),
                                    "client_initialized": diag.get("client_initialized"),
                                    "last_error": diag.get("last_error"),
                                    "BOX_JWT_JSON_present": bool(os.environ.get("BOX_JWT_JSON", "")),
                                })
                                return

                            box_results = []
                            for idx, row in queue.iterrows():
                                part_number = row.get("part_number", "")
                                attachments = []
                                if 'file_location' in row and row['file_location']:
                                    attachments = get_file_attachments(row['file_location'], logger)

                                upload_result = upload_and_share_for_part(
                                    box=box,
                                    row=row,
                                    attachments=attachments,
                                    access="company",
                                    default_expire_days=30,
                                )

                                if upload_result.get("error"):
                                    logger.warning(upload_result["error"])
                                    box_results.append({
                                        "part_number": part_number,
                                        "status": "Error",
                                        "detail": upload_result.get("error"),
                                    })
                                    continue

                                queue.loc[idx, 'box_rfq_root_id'] = getattr(upload_result.get('rfqs_root'), 'id', '')
                                queue.loc[idx, 'box_quote_folder_id'] = getattr(upload_result.get('quote_folder'), 'id', '')
                                queue.loc[idx, 'box_part_folder_id'] = getattr(upload_result.get('part_folder'), 'id', '')
                                queue.loc[idx, 'box_share_link'] = upload_result.get('share_link', '') or ''
                                queue.loc[idx, 'box_access'] = upload_result.get('box_access', '')
                                queue.loc[idx, 'box_password'] = upload_result.get('password', '') or ''
                                queue.loc[idx, 'box_unshared_at'] = upload_result.get('unshared_at', '') or ''
                                queue.loc[idx, 'box_last_updated'] = datetime.now().isoformat()
                                queue.loc[idx, 'files_uploaded'] = upload_result.get('files_uploaded', 0)
                                queue.loc[idx, 'file_manifest'] = upload_result.get('file_manifest', '')

                                box_results.append({
                                    "part_number": part_number,
                                    "status": "Updated",
                                    "box_part_folder_id": queue.loc[idx, 'box_part_folder_id'],
                                    "share_link": queue.loc[idx, 'box_share_link'],
                                })

                            queue.to_csv(queue_file, index=False)
                            results_df = pd.DataFrame(box_results)
                            st.success(f"Updated Box info for {len(results_df)} part(s) in entire queue.")
                            st.dataframe(results_df, use_container_width=True, hide_index=True)
                            logger.info(f"Box folders/links updated for entire queue: {len(results_df)} parts")
                    except Exception as e:
                        st.error(f"Error creating Box folders or updating CSV for entire queue: {str(e)}")
                        logger.error(f"Error creating Box folders or updating CSV for entire queue: {str(e)}")

                if st.button("Create Drafts for Entire Queue"):
                    if role not in ["admin", "editor"]:
                        st.warning("You need admin or editor privileges to send emails.")
                        return
                    
                    try:
                        with st.spinner("Processing entire queue..."):
                            # Get company info from CompanyInfo and override with user info
                            company_info = CompanyInfo.get_info()
                            company_info.update({
                                "sender_name": user["name"],
                                "sender_title": user.get("title", "Estimator"),
                                "sender_email": user.get("email", get_section("exchange").get("username", "")),
                                "sender_phone": user.get("phone", CompanyInfo.get_sender_phone())
                            })
                            
                            # Get exchange settings (Graph only)
                            ex_cfg = get_section("exchange")
                            exchange_settings = {
                                "username": ex_cfg.get("username", ""),
                                "cc": ex_cfg.get("cc")
                            }
                            
                            # Initialize Box (JWT)
                            box = BoxIntegration(logger=logger)
                            if not box or not box.client:
                                st.error("Box initialization failed. Check scripts\\box\\0__config.json or set BOX_CONFIG_PATH in settings.")
                                return

                            # Process the entire queue
                            results = []
                            
                            # Create a validator instance to reuse
                            validator = SpecProcessValidator()
                            
                            for _, row in queue.iterrows():
                                part_number = row["part_number"]
                                process = row["process"]
                                spec = row.get("spec", None)
                                
                                # Find vendors for this process and spec
                                matching_vendors = find_vendors_for_process_spec(
                                    vendor_info, 
                                    process, 
                                    spec, 
                                    validator
                                )
                                
                                if not matching_vendors:
                                    # Fallback: use VendorManager (config/vendors.json + contacts.csv)
                                    try:
                                        vm = VendorManager()
                                        vm_matches = vm.find_vendors_for_process_and_spec(process, spec)
                                        transformed = []
                                        for v in vm_matches:
                                            contact = vm.get_primary_contact(v)
                                            if contact and contact.get('email'):
                                                transformed.append({
                                                    'email': contact.get('email', ''),
                                                    'vendor_name': v.get('name', ''),
                                                    'first_name': contact.get('first_name', '') or contact.get('name', '')
                                                })
                                        matching_vendors = transformed
                                    except Exception as _e:
                                        logger.debug(f"VendorManager fallback error for {process}/{spec}: {_e}")
                                    if not matching_vendors:
                                        results.append({
                                            "part_number": part_number,
                                            "process": process,
                                            "status": "No vendors found",
                                            "emails_sent": 0
                                        })
                                        continue
                                
                                # Send emails to each vendor
                                emails_sent = 0
                                for vendor in matching_vendors:
                                    try:
                                        # Get vendor email and name
                                        vendor_email = vendor.get('email', '')
                                        vendor_name = vendor.get('vendor_name', '')
                                        contact_name = vendor.get('first_name', '')
                                        
                                        if not vendor_email:
                                            logger.warning(f"No email found for vendor: {vendor_name}")
                                            continue
                                        
                                        # Create email subject
                                        subject = f"RFQ for {part_number} - {process}"
                                        
                                        # Create email body
                                        body = create_email_body(
                                            queue_items=pd.DataFrame([row]),
                                            vendor_name=vendor_name,
                                            contact_name=contact_name,
                                            company_info=company_info
                                        )
                                        
                                        # Collect local files for Box upload
                                        attachments = []
                                        if 'file_location' in row and row['file_location']:
                                            file_path = row['file_location']
                                            attachments = get_file_attachments(file_path, logger)

                                        # Upload to Box and create share link (password if CUI/ITAR)
                                        upload_result = upload_and_share_for_part(
                                            box=box,
                                            row=row,
                                            attachments=attachments,
                                            access="company",
                                            default_expire_days=30,
                                        )

                                        if upload_result.get("error"):
                                            logger.warning(upload_result["error"]) 
                                            share_link = None
                                            is_cui = False
                                            password = None
                                        else:
                                            share_link = upload_result.get("share_link")
                                            is_cui = upload_result.get("is_cui", False)
                                            password = upload_result.get("password")

                                        # Inject Box link into the email body
                                        body_with_link = inject_box_link_into_body(body, share_link, is_cui)

                                        # Create the main draft (no attachments; link in body)
                                        if create_draft_email(
                                            recipient=vendor_email,
                                            subject=subject,
                                            body=body_with_link,
                                            attachments=None,
                                            cc=[exchange_settings.get('cc')] if exchange_settings.get('cc') else None,
                                            exchange_settings=exchange_settings
                                        ):
                                            emails_sent += 1
                                            logger.info(f"Draft email (with Box link) created for {vendor_email} for {part_number}")

                                            # If CUI/ITAR, create a second draft containing only the password
                                            if is_cui and password:
                                                pwd_subject = f"Password for RFQ Files – {part_number}"
                                                pwd_body = f"""
                                                <p>Hello {contact_name or ''},</p>
                                                <p>The RFQ files you received are password-protected.</p>
                                                <p><b>Password:</b> <code>{password}</code></p>
                                                <p>Please send this email about 10 minutes after the RFQ email.</p>
                                                """
                                                if create_draft_email(
                                                    recipient=vendor_email,
                                                    subject=pwd_subject,
                                                    body=pwd_body,
                                                    attachments=None,
                                                    cc=[exchange_settings.get('cc')] if exchange_settings.get('cc') else None,
                                                    exchange_settings=exchange_settings
                                                ):
                                                    logger.info(f"Password draft created for {vendor_email} for {part_number}")
                                                else:
                                                    logger.warning(f"Failed to create password draft for {vendor_email} for {part_number}")
                                        else:
                                            logger.warning(f"Failed to create draft email for {vendor_email} for {part_number}")
                                    except Exception as e:
                                        logger.error(f"Error creating draft email for {vendor.get('vendor_name', 'Unknown')} for {part_number}: {str(e)}")
                                
                                results.append({
                                    "part_number": part_number,
                                    "process": process,
                                    "status": "Success" if emails_sent > 0 else "Failed",
                                    "emails_sent": emails_sent
                                })
                            
                            # Display results
                            results_df = pd.DataFrame(results)
                            st.success(f"Processed {len(results)} parts. Created {results_df['emails_sent'].sum()} draft emails in Outlook.")
                            st.dataframe(results_df, use_container_width=True, hide_index=True)
                            
                            # Log the action
                            logger.info(f"Entire queue processed by {user['name']}, draft emails created")
                            
                    except Exception as e:
                        st.error(f"Error creating draft emails for queue: {str(e)}")
                        logger.error(f"Error creating draft emails for queue: {str(e)}")
        
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            logger.error(f"Error loading data: {str(e)}")
            
    except Exception as e:
        st.error(f"Error loading queue data: {str(e)}")
        logger.error(f"Error loading queue data: {str(e)}")


def display_email_settings():
    """Display email settings from configuration."""
    st.subheader("Email Settings")
    
    # Display current settings
    st.info("""
    Email settings are configured in the Streamlit secrets file. 
    Current configuration is displayed below for reference only.
    To change these settings, edit the .streamlit/secrets.toml file directly.
    """)
    
    # Display settings in expandable section
    with st.expander("View Current Email Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Mailbox Settings (Graph)**")
            ex_cfg = get_section("exchange")
            st.text(f"Mailbox (UPN): {ex_cfg.get('username', '')}")
            st.text(f"Default CC: {ex_cfg.get('cc', '')}")
        
        with col2:
            st.markdown("**Company Settings**")
            st.text(f"Company Name: {CompanyInfo.get_name()}")
            st.text(f"Sender Name: {CompanyInfo.get_sender_name()}")
            st.text(f"Sender Title: {CompanyInfo.get_sender_title()}")
            st.text(f"Sender Phone: {CompanyInfo.get_sender_phone()}")
    
    # New: Box Settings and Diagnostics
    with st.expander("Box Settings (JWT) and Diagnostics"):
        # Show current BOX_CONFIG_PATH
        current_path = os.environ.get("BOX_CONFIG_PATH", "")
        st.text(f"Current BOX_CONFIG_PATH: {current_path or '(not set)'}")
        # Also indicate if BOX_JWT_JSON (full credentials in secrets) is present
        jwt_json_env = os.environ.get("BOX_JWT_JSON", "")
        st.text(f"BOX_JWT_JSON present: {'yes' if jwt_json_env else 'no'}" + (f" (len={len(jwt_json_env)})" if jwt_json_env else ""))
        st.caption("Search order: 1) BOX_JWT_JSON (secrets)  2) BOX_CONFIG_PATH  3) scripts\\box\\0__config.json  4) scripts\\0__config.json")

        # Allow session override for BOX_CONFIG_PATH
        new_path = st.text_input("Set/override BOX_CONFIG_PATH for this session", value=current_path)
        set_env = st.button("Use This Config Path (Session Only)")
        if set_env:
            try:
                if new_path:
                    os.environ["BOX_CONFIG_PATH"] = new_path
                    st.success(f"BOX_CONFIG_PATH set for this session: {new_path}")
                    logger.info(f"BOX_CONFIG_PATH set via UI: {new_path}")
                else:
                    if "BOX_CONFIG_PATH" in os.environ:
                        del os.environ["BOX_CONFIG_PATH"]
                    st.warning("Cleared BOX_CONFIG_PATH for this session.")
                    logger.info("BOX_CONFIG_PATH cleared via UI")
            except Exception as e:
                st.error(f"Failed to set BOX_CONFIG_PATH: {e}")
                logger.error(f"Failed to set BOX_CONFIG_PATH: {e}")

        # Test connection
        if st.button("Test Box Connection"):
            try:
                box = BoxIntegration(logger=logger)
                # Safely gather diagnostics even if older BoxIntegration lacks .diagnostics()
                diag = {}
                try:
                    if box and hasattr(box, "diagnostics"):
                        diag = box.diagnostics()
                    elif box:
                        diag = {
                            "tried_paths": getattr(box, "tried_paths", []),
                            "config_path": getattr(box, "config_path", None),
                            "last_error": getattr(box, "last_error", ""),
                            "client_initialized": bool(getattr(box, "client", None)),
                            "user": getattr(box, "_user_identity", ""),
                        }
                    else:
                        diag = {"client_initialized": False, "last_error": "Box object not created"}
                except Exception as _e:
                    diag = {"client_initialized": bool(box and getattr(box, "client", None)), "last_error": str(_e)}
                if box and getattr(box, "client", None):
                    st.success(f"Authenticated to Box as {diag.get('user','')}\nConfig: {diag.get('config_path','')}")
                else:
                    st.error("Box initialization failed.")
                # Show diagnostics details
                st.write({
                    "config_path": diag.get("config_path"),
                    "tried_paths": diag.get("tried_paths"),
                    "client_initialized": diag.get("client_initialized"),
                    "last_error": diag.get("last_error"),
                    "BOX_JWT_JSON_present": bool(os.environ.get("BOX_JWT_JSON", "")),
                })
            except Exception as e:
                st.error(f"Box test failed: {e}")
                logger.error(f"Box test failed: {e}")
    
    # Test email button
    if st.button("Create Test Email Draft"):
        try:
            # Mailbox settings (Graph)
            ex_cfg = get_section("exchange")
            to_addr = ex_cfg.get("username", "")
            cc_addr = ex_cfg.get("cc")
            
            # Create a test email
            test_email = {
                "to": to_addr,
                "subject": "Test RFQ Email",
                "body": "<h1>Test Email</h1><p>This is a test email from the RFQ Sender application.</p>",
                "cc": [cc_addr] if cc_addr else [],
                "attachments": []
            }
            
            # Create the test email draft
            if create_draft_email(
                recipient=test_email["to"],
                subject=test_email["subject"],
                body=test_email["body"],
            ):
                st.success("Test email draft created successfully in Outlook!")
                logger.info("Test email draft created successfully in Outlook")
            else:
                st.error("Failed to create test email draft.")
                logger.error("Failed to create test email draft")
            
        except Exception as e:
            st.error(f"Error creating test email draft: {str(e)}")
            logger.error(f"Error creating test email draft: {str(e)}")


def main():
    """Main function to run the page."""
    setup_page()
    
    # Get user from session state (set in main app)
    if "user" not in st.session_state:
        st.warning("Please select a user in the sidebar of the main page.")
        return
    
    user = st.session_state.user
    role = get_user_role(user)
    
    # Display user info
    st.sidebar.markdown(f"**User:** {user['name']}")
    st.sidebar.markdown(f"**Role:** {role}")
    
    # Display email settings
    display_email_settings()
    
    # Display queue for sending emails
    display_queue_for_emails(user, role)


if __name__ == "__main__":
    main()