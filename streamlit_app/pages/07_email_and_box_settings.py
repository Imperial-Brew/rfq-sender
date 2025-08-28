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
from utils.rfq_queue import save_queue, load_queue as load_queue_df
from core.secrets import get_section
from core.email.email_manager import EmailManager
from core.vendors.vendor_manager import VendorManager
from streamlit_app.utils.auth_shim import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication
from scripts.utils.spec_check import SpecProcessValidator
from utils.rfq_tracking import get_tracker
from scripts.box.box_integration import BoxIntegration
from boxsdk.exception import BoxAPIException
import secrets
import string

# Check authentication
if not require_authentication():
    st.stop()

# Initialize configuration
init_config()

# Set up logging
logger = LoggingConfig.setup_logging(__name__, "send_rfq_emails.log")

# Moved vendor helpers to a utility module for maintainability
from streamlit_app.utils.vendor_helpers import (
    normalize_process_spec,
    build_familiarity_report,
    find_vendors_for_process_spec,
)

# Box helpers moved to a utility module for maintainability
from streamlit_app.utils.box_helpers import (
    detect_cui_itar,
    generate_password,
    ensure_rfq_part_folder,
    upload_and_share_for_part,
    persist_box_update as _persist_box_update,
)

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
            logger.info(f"Local queue file not found at {queue_file}; will try Box/central loader")
        else:
            print(f"Local queue file not found at {queue_file}; will try Box/central loader")

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
        # Load queue using a centralized loader (Box-backed if configured)
        try:
            queue = load_queue_df()
            if queue is None or queue.empty:
                # Fallback to local CSV path if centralized loader returns empty and file exists
                if os.path.exists(queue_file):
                    try:
                        queue = pd.read_csv(queue_file, encoding='utf-8')
                    except UnicodeDecodeError:
                        queue = pd.read_csv(queue_file, encoding='cp1252')
                else:
                    queue = pd.DataFrame()
        except Exception as _e:
            # Fallback to direct CSV read on error
            if logger:
                logger.warning(f"load_queue_df failed ({_e}); falling back to CSV at {queue_file}")
            if os.path.exists(queue_file):
                try:
                    queue = pd.read_csv(queue_file, encoding='utf-8')
                except UnicodeDecodeError:
                    queue = pd.read_csv(queue_file, encoding='cp1252')
            else:
                queue = pd.DataFrame()

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
            'RFQ #': 'rfq #',  # keep normalized but we will hide it in display
            'Part_Number': 'part_number',
            'Rev': 'rev',  # normalize to lowercase
            'Print Callout': 'callout',
            'process': 'process',
            'spec': 'spec',
            'material': 'material',
            'quantities': 'quantities',
            'file_location': 'file_location',
            'submitted_by': 'submitted_by',
            'qt/so #': 'qt/so #',
        }
        
        # Rename columns
        queue = queue.rename(columns=queue_column_mapping)

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








def inject_box_link_into_body(html_body: str, share_link: str, is_cui: bool) -> str:
    """Append a styled Box link section to the existing HTML email body and then append signature."""
    if not share_link:
        # Even if no link, ensure signature is appended
        return append_signature(html_body)

    banner = f"""
    <div style=\"margin-top:16px;padding:14px;border:1px solid #d0d7de;border-radius:8px;background:#f6f8fa;\">
      <div style=\"font-size:16px;font-weight:600;margin-bottom:6px;\">
        RFQ Files in Box { '(Password Protected)' if is_cui else '' }
      </div>
      <div>
        <a href=\"{share_link}\" style=\"display:inline-block;padding:10px 14px;background:#2d7ff9;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;\">
          Open RFQ Folder
        </a>
      </div>
      <div style=\"margin-top:8px;color:#57606a;font-size:13px;\">
        If you have trouble opening the link, copy and paste this URL into your browser:<br/>
        <code style=\"font-size:12px;\">{share_link}</code>
      </div>
    </div>
    """
    updated = html_body
    if "</body>" in html_body:
        updated = html_body.replace("</body>", banner + "\n</body>")
    elif "</html>" in html_body:
        updated = html_body.replace("</html>", banner + "\n</html>")
    else:
        updated = html_body + banner
    # Append signature after Box banner
    return append_signature(updated)


def load_signature_html() -> str:
    """Load the HTML signature from docs/templates/email_signature.html."""
    try:
        sig_path = os.path.join(parent_dir, 'docs', 'templates', 'email_signature.html')
        if os.path.exists(sig_path):
            with open(sig_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        logger.debug(f"Could not load email signature: {e}")
    return ""


def append_signature(html_body: str) -> str:
    """Append the HTML signature at the end of the email body."""
    signature = load_signature_html()
    if not signature:
        return html_body
    if "</body>" in html_body:
        return html_body.replace("</body>", signature + "\n</body>")
    if "</html>" in html_body:
        return html_body.replace("</html>", signature + "\n</html>")
    return html_body + signature



def _load_sample_table_header(csv_path: str) -> List[str]:
    """Load header columns from the sample table CSV; fallback to defaults if missing."""
    default_header = [
        "Part Number",
        "Print Callout",
        "Process",
        "Spec",
        "QTYs",
        "Unit_Price",
        "Line Minimum",
        "Order Minimum",
        "Lead_Time",
        "vendor_ref_#",
    ]
    try:
        if csv_path and os.path.exists(csv_path):
            import csv
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header and len(header) >= 5:
                    return header
    except UnicodeDecodeError:
        try:
            import csv
            with open(csv_path, 'r', newline='', encoding='cp1252', errors='replace') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header and len(header) >= 5:
                    return header
        except Exception:
            pass
    except Exception:
        pass
    return default_header


def _build_sample_table_html(row: Any, header: List[str]) -> str:
    """Build a single-row HTML sample table using provided header and queue row fields."""
    # Map row fields
    def _safe(val):
        try:
            return '' if val is None or (isinstance(val, float) and pd.isna(val)) else str(val)
        except Exception:
            return ''
    part_number = _safe(row.get('part_number', '') if hasattr(row, 'get') else getattr(row, 'part_number', ''))
    callout = _safe(row.get('callout', '') if hasattr(row, 'get') else getattr(row, 'callout', ''))
    process = _safe(row.get('process', '') if hasattr(row, 'get') else getattr(row, 'process', ''))
    spec = _safe(row.get('spec', '') if hasattr(row, 'get') else getattr(row, 'spec', ''))
    qtys = _safe(row.get('qty', None) if hasattr(row, 'get') else getattr(row, 'qty', None))
    if not qtys:
        qtys = _safe(row.get('quantities', '') if hasattr(row, 'get') else getattr(row, 'quantities', ''))

    # Build cells aligned to expected header names; unknown headers get empty cells
    values_map = {
        'part number': part_number,
        'print callout': callout,
        'process': process,
        'spec': spec,
        'qtys': qtys,
        'unit_price': '',
        'line minimum': '',
        'order minimum': '',
        'lead_time': '',
        'vendor_ref_#': '',
        'vendor_ref': '',
    }
    def norm(s: str) -> str:
        return s.lower().replace(' ', '').replace('-', '').replace('/', '').strip()

    html = ['<table style="border-collapse: collapse; width: 100%;">']
    # Header row
    html.append('<tr style="background-color: #f2f2f2; font-weight: bold;">')
    for col in header:
        html.append(f'<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">{col}</th>')
    html.append('</tr>')
    # Data row
    html.append('<tr>')
    for col in header:
        key = norm(col)
        val = ''
        if key in values_map:
            val = values_map[key]
        else:
            # try specific normalized keys
            if key == 'partnumber':
                val = part_number
            elif key == 'printcallout':
                val = callout
            elif key == 'leadtime':
                val = ''
            elif key == 'qty' or key == 'qtys':
                val = qtys
            else:
                val = ''
        html.append(f'<td style="border: 1px solid #ddd; padding: 8px;">{val}</td>')
    html.append('</tr>')
    html.append('</table>')
    return ''.join(html)


def create_email_body(queue_items: pd.DataFrame, 
                     vendor_name: str, 
                     contact_name: str = None,
                     company_info: Dict[str, str] = None) -> str:
    """
    Create HTML email body for RFQ using the docs/templates/cover_letter.j2 template.

    This returns the body without the signature; the signature will be appended
    after Box link injection to match policy (link appears above signature).
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

    # Jinja2 environment for docs/templates
    template_dir = os.path.join(parent_dir, 'docs', 'templates')
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        autoescape=jinja2.select_autoescape(['html', 'xml'])
    )

    # Load cover_letter.j2; if missing, fall back to a minimal greeting
    try:
        template = env.get_template('cover_letter.j2')
    except jinja2.exceptions.TemplateNotFound:
        # Minimal fallback
        greeting = f"Hello {contact_name}," if contact_name else "Hello," 
        return f"<p>{greeting}</p><p>Please see the RFQ details below.</p>"

    # Prepare context expected by cover_letter.j2
    # Use first row since we generate one email per vendor/part in this UI
    row = queue_items.iloc[0] if not queue_items.empty else {}

    # Parse quantities if present (string or list); keep simple representation
    q_val = ''
    try:
        q_val = row.get('quantities', '') if isinstance(row, dict) else row.get('quantities')
    except Exception:
        q_val = ''

    from datetime import datetime, timedelta
    due_date = (datetime.now() + timedelta(days=7)).strftime("%B %d, %Y")

    # Attempt to build sample table from CSV header template
    sample_csv = os.path.join(parent_dir, 'docs', 'templates', 'Sample_Table(Empty)-OS.csv')
    sample_table_html = None
    try:
        header = _load_sample_table_header(sample_csv)
        sample_table_html = _build_sample_table_html(row, header)
    except Exception as _e:
        logger.debug(f"Sample table generation skipped: {_e}")
        sample_table_html = None

    context = {
        'vendor': {
            'name': vendor_name,
            'first_name': contact_name or vendor_name,
        },
        'greeting_name': contact_name or vendor_name,
        'part_no': str(row.get('part_number', '')) if hasattr(row, 'get') else str(getattr(row, 'part_number', '')),
        'process': str(row.get('process', '')) if hasattr(row, 'get') else str(getattr(row, 'process', '')),
        'spec': (row.get('spec', None) if hasattr(row, 'get') else getattr(row, 'spec', None)) or None,
        'quantities': q_val,
        'attachments': [],  # We use Box link; no direct attachments from this UI
        'due_date': due_date,
        'sender_name': company_info.get('sender_name', ''),
        'sender_email': company_info.get('sender_email', ''),
        'company_name': company_info.get('name', ''),
        'sample_table': sample_table_html,
    }

    try:
        return template.render(**context)
    except Exception as e:
        logger.warning(f"Failed to render cover_letter.j2: {e}")
        greeting = f"Hello {contact_name}," if contact_name else "Hello," 
        return f"<p>{greeting}</p><p>Please see the RFQ details below.</p>"


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
    st.title("Email and Box settings")
    st.markdown("""
    This page allows you to configure and use email + Box operations for RFQs, including creating draft emails and managing Box folders/links for parts in the queue.
    
    > Note: Drafts are created in your Outlook client; you must review and send them manually.
    """)


def display_email_settings():
    """Backward-compatible no-op after UI refactor.
    Kept to avoid runtime errors where older code still calls this function.
    Settings controls have been moved into the queue section and/or sidebar.
    """
    # Intentionally does nothing. Previously contained email settings UI.
    return


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

            display_df = display_df.drop(columns=["rfq #", "RFQ #"], errors="ignore")

            # Reorder and select columns for display
            columns_to_display = ["part_number", "rev", "process", "spec", "quantities"]
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


            # Initialize RFQ tracker
            tracker = get_tracker()

            # Queue Management Tools
            with st.expander("Queue Management Tools", expanded=False):
                # Duplicate handling policy for RFQ Master logging
                dup_policy_label = "When logging to RFQ Master, if a matching entry already exists (same qt/so #, part, process, vendor, contact):"
                dup_choice = st.radio(
                    dup_policy_label,
                    options=["Skip (do not add new line)", "Update (status/notes/link/date)", "Append (always add new line)"],
                    index=0,
                    key="rfq_master_dup_policy",
                    help=(
                        "Skip: return existing rfq# and do not write.\n"
                        "Update: update status/notes/rfq_folder/date on the existing line.\n"
                        "Append: always add a new row even if a match exists."
                    ),
                )
                # Map UI choice to on_duplicate parameter
                _on_dup_map = {
                    "Skip (do not add new line)": "skip",
                    "Update (status/notes/link/date)": "update",
                    "Append (always add new line)": "append",
                }
                on_duplicate_policy = _on_dup_map.get(dup_choice, "skip")
                if st.button("Refresh queue from Box"):
                    try:
                        from utils.rfq_queue import _get_box_store as _qm_get_box_store
                        from utils.rfq_queue import _standardize_df as _qm_std_df
                        from utils.rfq_queue import save_queue as _qm_save_queue

                        with st.spinner("Refreshing queue from Box..."):
                            store = _qm_get_box_store()
                            if store is None:
                                st.error(
                                    "Box is not configured or failed to initialize; cannot refresh from Box.\n"
                                    "Check BOX_QUEUE_FILE_ID / BOX_QUEUE_FOLDER_ID and Box credentials."
                                )
                            else:
                                refreshed_df = store.load_df()
                                refreshed_df = _qm_std_df(refreshed_df)
                                queue = refreshed_df
                                st.success(f"Loaded {len(queue)} row(s) from Box and refreshed the queue in the UI.")
                                st.dataframe(queue, use_container_width=True, hide_index=True)

                                if st.button("Save cleaned queue back to Box (drop legacy columns)"):
                                    try:
                                        _qm_save_queue(queue)
                                        st.success("Cleaned queue saved back to Box. Legacy columns have been dropped.")
                                    except Exception as _e:
                                        st.error(f"Failed to save cleaned queue back to Box: {_e}")
                                        logger.error(f"Failed to save cleaned queue back to Box: {_e}")
                    except Exception as e:
                        st.error(f"Refresh from Box failed: {e}")
                        logger.exception("Refresh from Box failed")

                # Validate process/spec against familiar list
                try:
                    if st.button("Validate process/spec against familiar list"):
                        report_df = build_familiarity_report(queue)
                        if report_df.empty:
                            st.success("All rows have familiar process/spec values.")
                        else:
                            st.warning(f"Found {len(report_df)} row(s) with unfamiliar process/spec.")
                            st.dataframe(report_df, use_container_width=True, hide_index=True)
                            st.download_button(
                                "Download report CSV",
                                data=report_df.to_csv(index=False).encode('utf-8'),
                                file_name="unfamiliar_process_spec_report.csv",
                                mime="text/csv",
                            )
                except Exception as e:
                    st.error(f"Error running familiarity validation: {e}")
                    logger.exception("Error running familiarity validation")

            # Process selected parts
            col1, col2 = st.columns(2)
            
            with col1:
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
                                st.error(
                                    "Box initialization failed. Provide [box].jwt_json in Streamlit Secrets or set BOX_CONFIG_PATH to your 0__config.json. See diagnostics below.")
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
                                    access="open",
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
                                queue.loc[idx, 'box_part_folder_id'] = getattr(upload_result.get('part_folder'), 'id',
                                                                               '')
                                queue.loc[idx, 'box_share_link'] = upload_result.get('share_link', '') or ''
                                queue.loc[idx, 'box_password'] = upload_result.get('password', '') or ''
                                queue.loc[idx, 'box_unshared_at'] = upload_result.get('unshared_at', '') or ''
                                try:
                                    part_folder_obj = upload_result.get('part_folder')
                                    if part_folder_obj is not None:
                                        folder = box.client.folder(part_folder_obj.id).get()
                                        api_last_modified = getattr(folder, 'content_modified_at', None) or getattr(
                                            folder, 'modified_at', None)
                                        queue.loc[idx, 'box_last_modified'] = api_last_modified or ''
                                except Exception as _e:
                                    logger.debug(f"Failed to fetch Box folder modified time: {_e}")
                                queue.loc[idx, 'files_uploaded'] = upload_result.get('files_uploaded', 0)

                                # New: create an open, no-password share link for the quote folder
                                quote_folder = upload_result.get('quote_folder')
                                quote_share_link = box.create_share_link(
                                    quote_folder,
                                    access="open",
                                    password=None,
                                    expire_days=None,
                                ) if quote_folder else None
                                queue.loc[idx, 'box_rfq_folder'] = quote_share_link or ''

                                box_results.append({
                                    "part_number": part_number,
                                    "status": "Updated",
                                    "box_part_folder_id": queue.loc[idx, 'box_part_folder_id'],
                                    "share_link": queue.loc[idx, 'box_share_link'],
                                    "box_rfq_folder": queue.loc[idx, 'box_rfq_folder'],  # optional
                                })

                            # Save queue via centralized Box/local handler
                            save_queue(queue)
                            results_df = pd.DataFrame(box_results)
                            st.success(f"Updated Box info for {len(results_df)} selected part(s).")
                            st.dataframe(results_df, use_container_width=True, hide_index=True)
                            logger.info(f"Box folders/links updated for {len(results_df)} selected parts")
                    except Exception as e:
                        st.error(f"Error creating Box folders or updating CSV: {str(e)}")
                        logger.error(f"Error creating Box folders or updating CSV: {str(e)}")

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
                                
                                # Determine Box link/password ONCE per part
                                share_link = row.get('box_share_link') or None
                                password = row.get('box_password') or None
                                is_cui = detect_cui_itar(row)

                                if not share_link:
                                    # Collect local files for Box upload once
                                    attachments_once = []
                                    if 'file_location' in row and row['file_location']:
                                        attachments_once = get_file_attachments(row['file_location'], logger)

                                    upload_result_once = upload_and_share_for_part(
                                        box=box,
                                        row=row,
                                        attachments=attachments_once,
                                        access="open",
                                        default_expire_days=30,
                                    )

                                    if upload_result_once.get("error"):
                                        logger.warning(upload_result_once["error"]) 
                                        share_link = None
                                        is_cui = False
                                        password = None
                                    else:
                                        share_link = upload_result_once.get("share_link")
                                        is_cui = upload_result_once.get("is_cui", is_cui)
                                        password = upload_result_once.get("password")

                                        # Persist new Box info to the queue for this row
                                        # New: ensure quote-level open link (no password, no expiry)
                                        quote_folder = upload_result_once.get('quote_folder')
                                        quote_share_link = box.create_share_link(
                                            quote_folder,
                                            access="open",
                                            password=None,
                                            expire_days=None,
                                        ) if quote_folder else None
                                        queue.loc[row.name, 'box_rfq_folder'] = quote_share_link or ''
                                        queue.loc[row.name, 'box_share_link'] = share_link or ''
                                        queue.loc[row.name, 'box_password'] = password or ''
                                        queue.loc[row.name, 'box_unshared_at'] = upload_result_once.get('unshared_at', '') or ''
                                        queue.loc[row.name, 'box_last_updated'] = datetime.now().isoformat()
                                        queue.loc[row.name, 'files_uploaded'] = upload_result_once.get('files_uploaded', 0)
                                        save_queue(queue)
                                else:
                                    # If link exists but password missing and it's CUI, ensure we have a password
                                    if is_cui and not password:
                                        attachments_once = []
                                        if 'file_location' in row and row['file_location']:
                                            attachments_once = get_file_attachments(row['file_location'], logger)
                                        upload_result_once = upload_and_share_for_part(
                                            box=box,
                                            row=row,
                                            attachments=attachments_once,
                                            access="open",
                                            default_expire_days=30,
                                        )
                                        if not upload_result_once.get("error"):
                                            password = upload_result_once.get('password')
                                            # Keep existing share_link if present, but update stored password
                                            queue.loc[row.name, 'box_password'] = password or ''
                                            queue.loc[row.name, 'box_last_updated'] = datetime.now().isoformat()
                                            save_queue(queue)

                                # Send emails to each vendor using the determined link/password
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
                                                pwd_subject = f"RFQ Files – {part_number}"
                                                pwd_body = f"""
                                                <p>Hello {contact_name or ''},</p>
                                                <p>The RFQ files you received are password-protected.</p>
                                                <p><b>Password:</b> <code>{password}</code></p>
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
            
            with col1:
                # New: Log RFQs to master for selected parts (no email)
                if st.button("Log RFQs to Master for Selected Parts", disabled=len(selected_indices) == 0):
                    try:
                        with st.spinner("Logging RFQs to master for selected parts..."):
                            logged = 0
                            # Reuse vendor_info built earlier and SpecProcessValidator
                            validator = SpecProcessValidator()
                            for _, row in queue.iloc[selected_indices].iterrows():
                                part_number = row.get("part_number", "")
                                process = row.get("process", "")
                                spec = row.get("spec", None)
                                matching_vendors = find_vendors_for_process_spec(
                                    vendor_info,
                                    process,
                                    spec,
                                    validator
                                )
                                if not matching_vendors:
                                    continue
                                for vendor in matching_vendors:
                                    vendor_email = vendor.get('email', '')
                                    vendor_name = vendor.get('vendor_name', '')
                                    contact_name = vendor.get('first_name', '')
                                    if not vendor_email:
                                        continue
                                    try:
                                        tracker.add_master_entry(
                                            row.to_dict(),
                                            vendor_name=vendor_name,
                                            contact_email=vendor_email,
                                            contact_name=contact_name,
                                            status="pending",
                                            dedupe=True,
                                            on_duplicate=on_duplicate_policy,
                                        )
                                        logged += 1
                                    except Exception as _e:
                                        logger.warning(f"Failed to append RFQ master for {part_number}/{vendor_email}: {_e}")
                            st.success(f"Logged {logged} RFQ entrie(s) to rfq_master.csv")
                    except Exception as e:
                        st.error(f"Error logging RFQs to master: {e}")
                        logger.error(f"Error logging RFQs to master: {e}")

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
                                    access="open",
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

                                queue.loc[idx, 'box_part_folder_id'] = getattr(upload_result.get('part_folder'), 'id', '')
                                queue.loc[idx, 'box_share_link'] = upload_result.get('share_link', '') or ''
                                queue.loc[idx, 'box_password'] = upload_result.get('password', '') or ''
                                queue.loc[idx, 'box_unshared_at'] = upload_result.get('unshared_at', '') or ''
                                try:
                                    part_folder_obj = upload_result.get('part_folder')
                                    if part_folder_obj is not None:
                                        folder = box.client.folder(part_folder_obj.id).get()
                                        api_last_modified = getattr(folder, 'content_modified_at', None) or getattr(folder, 'modified_at', None)
                                        queue.loc[idx, 'box_last_modified'] = api_last_modified or ''
                                except Exception as _e:
                                    logger.debug(f"Failed to fetch Box folder modified time: {_e}")
                                queue.loc[idx, 'files_uploaded'] = upload_result.get('files_uploaded', 0)

                                # Ensure quote-level open link (no password, no expiry)
                                quote_folder = upload_result.get('quote_folder')
                                quote_share_link = box.create_share_link(
                                    quote_folder,
                                    access="open",
                                    password=None,
                                    expire_days=None,
                                ) if quote_folder else None
                                queue.loc[idx, 'box_rfq_folder'] = quote_share_link or ''

                                box_results.append({
                                    "part_number": part_number,
                                    "status": "Updated",
                                    "box_part_folder_id": queue.loc[idx, 'box_part_folder_id'],
                                    "share_link": queue.loc[idx, 'box_share_link'],
                                })

                            save_queue(queue)
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
                                
                                # Determine Box link/password ONCE per part (entire queue)
                                share_link = row.get('box_share_link') or None
                                password = row.get('box_password') or None
                                is_cui = detect_cui_itar(row)

                                if not share_link:
                                    attachments_once = []
                                    if 'file_location' in row and row['file_location']:
                                        attachments_once = get_file_attachments(row['file_location'], logger)

                                    upload_result_once = upload_and_share_for_part(
                                        box=box,
                                        row=row,
                                        attachments=attachments_once,
                                        access="open",
                                        default_expire_days=30,
                                    )

                                    if upload_result_once.get("error"):
                                        logger.warning(upload_result_once["error"]) 
                                        share_link = None
                                        is_cui = False
                                        password = None
                                    else:
                                        share_link = upload_result_once.get("share_link")
                                        is_cui = upload_result_once.get("is_cui", is_cui)
                                        password = upload_result_once.get("password")

                                        # Persist new Box info to the queue for this row
                                        # New: ensure quote-level open link (no password, no expiry)
                                        quote_folder = upload_result_once.get('quote_folder')
                                        quote_share_link = box.create_share_link(
                                            quote_folder,
                                            access="open",
                                            password=None,
                                            expire_days=None,
                                        ) if quote_folder else None
                                        queue.loc[row.name, 'box_rfq_folder'] = quote_share_link or ''
                                        queue.loc[row.name, 'box_part_folder_id'] = getattr(upload_result_once.get('part_folder'), 'id', '')
                                        queue.loc[row.name, 'box_share_link'] = share_link or ''
                                        queue.loc[row.name, 'box_password'] = password or ''
                                        queue.loc[row.name, 'box_unshared_at'] = upload_result_once.get('unshared_at', '') or ''
                                        queue.loc[row.name, 'box_last_updated'] = datetime.now().isoformat()
                                        queue.loc[row.name, 'files_uploaded'] = upload_result_once.get('files_uploaded', 0)
                                        save_queue(queue)
                                else:
                                    # If link exists but password missing and it's CUI, ensure we have a password
                                    if is_cui and not password:
                                        attachments_once = []
                                        if 'file_location' in row and row['file_location']:
                                            attachments_once = get_file_attachments(row['file_location'], logger)
                                        upload_result_once = upload_and_share_for_part(
                                            box=box,
                                            row=row,
                                            attachments=attachments_once,
                                            access="open",
                                            default_expire_days=30,
                                        )
                                        if not upload_result_once.get("error"):
                                            password = upload_result_once.get('password')
                                            queue.loc[row.name, 'box_password'] = password or ''
                                            queue.loc[row.name, 'box_last_updated'] = datetime.now().isoformat()
                                            save_queue(queue)

                                # Send emails to each vendor using the determined link/password
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
                                                pwd_subject = f"RFQ Files – {part_number}"
                                                pwd_body = f"""
                                                <p>Hello {contact_name or ''},</p>
                                                <p>The RFQ files you received are password-protected.</p>
                                                <p><b>Password:</b> <code>{password}</code></p>
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

                # New: Log RFQs to master for entire queue (no email)
                if st.button("Log RFQs to Master for Entire Queue"):
                    try:
                        with st.spinner("Logging RFQs to master for entire queue..."):
                            logged = 0
                            validator = SpecProcessValidator()
                            for _, row in queue.iterrows():
                                part_number = row.get("part_number", "")
                                process = row.get("process", "")
                                spec = row.get("spec", None)
                                matching_vendors = find_vendors_for_process_spec(
                                    vendor_info,
                                    process,
                                    spec,
                                    validator
                                )
                                if not matching_vendors:
                                    continue
                                for vendor in matching_vendors:
                                    vendor_email = vendor.get('email', '')
                                    vendor_name = vendor.get('vendor_name', '')
                                    contact_name = vendor.get('first_name', '')
                                    if not vendor_email:
                                        continue
                                    try:
                                        tracker.add_master_entry(
                                            row.to_dict(),
                                            vendor_name=vendor_name,
                                            contact_email=vendor_email,
                                            contact_name=contact_name,
                                            status="pending",
                                            dedupe=True,
                                            on_duplicate=on_duplicate_policy,
                                        )
                                        logged += 1
                                    except Exception as _e:
                                        logger.warning(f"Failed to append RFQ master for {part_number}/{vendor_email}: {_e}")
                            st.success(f"Logged {logged} RFQ entrie(s) to rfq_master.csv")
                    except Exception as e:
                        st.error(f"Error logging RFQs to master: {e}")
                        logger.error(f"Error logging RFQs to master: {e}")

        except Exception as e:
            st.error(f"Error loading queue data: {str(e)}")
            logger.error(f"Error loading queue data: {str(e)}")
    except Exception as e:
        st.error(f"Error loading queue data: {str(e)}")
        logger.error(f"Error loading queue data: {str(e)}")


# def display_email_settings():
#     """Display email settings from the configuration."""
#     st.subheader("Email Settings")
    
    # Display current settings
    # st.info("""
    # Email settings are configured in the Streamlit secrets file.
    # Current configuration is displayed below for reference only.
    # To change these settings, edit the .streamlit/secrets.toml file directly.
    # """)
    
    # Display settings in an expandable section
    # with st.expander("View Current Email Settings"):
    #     col1, col2 = st.columns(2)
    #
    #     with col1:
    #         st.markdown("**Mailbox Settings (Graph)**")
    #         ex_cfg = get_section("exchange")
    #         st.text(f"Mailbox (UPN): {ex_cfg.get('username', '')}")
    #         st.text(f"Default CC: {ex_cfg.get('cc', '')}")
    #
    #     with col2:
    #         st.markdown("**Company Settings**")
    #         st.text(f"Company Name: {CompanyInfo.get_name()}")
    #         st.text(f"Sender Name: {CompanyInfo.get_sender_name()}")
    #         st.text(f"Sender Title: {CompanyInfo.get_sender_title()}")
    #         st.text(f"Sender Phone: {CompanyInfo.get_sender_phone()}")
    
    # New: Box Settings and Diagnostics
    # with st.expander("Box Settings (JWT) and Diagnostics"):
    #     # Show current BOX_CONFIG_PATH
    #     current_path = os.environ.get("BOX_CONFIG_PATH", "")
    #     st.text(f"Current BOX_CONFIG_PATH: {current_path or '(not set)'}")
    #     # Also indicate if BOX_JWT_JSON (full credentials in secrets) is present
    #     jwt_json_env = os.environ.get("BOX_JWT_JSON", "")
    #     st.text(f"BOX_JWT_JSON present: {'yes' if jwt_json_env else 'no'}" + (f" (len={len(jwt_json_env)})" if jwt_json_env else ""))
    #     st.caption("Search order: 1) BOX_JWT_JSON (secrets)  2) BOX_CONFIG_PATH  3) scripts\\box\\0__config.json  4) scripts\\0__config.json")
#
    #     # Allow session override for BOX_CONFIG_PATH
    #     new_path = st.text_input("Set/override BOX_CONFIG_PATH for this session", value=current_path)
    #     set_env = st.button("Use This Config Path (Session Only)")
    #     if set_env:
    #         try:
    #             if new_path:
    #                 os.environ["BOX_CONFIG_PATH"] = new_path
    #                 st.success(f"BOX_CONFIG_PATH set for this session: {new_path}")
    #                 logger.info(f"BOX_CONFIG_PATH set via UI: {new_path}")
    #             else:
    #                 if "BOX_CONFIG_PATH" in os.environ:
    #                     del os.environ["BOX_CONFIG_PATH"]
    #                 st.warning("Cleared BOX_CONFIG_PATH for this session.")
    #                 logger.info("BOX_CONFIG_PATH cleared via UI")
    #         except Exception as e:
    #             st.error(f"Failed to set BOX_CONFIG_PATH: {e}")
    #             logger.error(f"Failed to set BOX_CONFIG_PATH: {e}")
#
    #     # Test connection
    #     if st.button("Test Box Connection"):
    #         try:
    #             box = BoxIntegration(logger=logger)
    #             # Safely gather diagnostics even if older BoxIntegration lacks .diagnostics()
    #             diag = {}
    #             try:
    #                 if box and hasattr(box, "diagnostics"):
    #                     diag = box.diagnostics()
    #                 elif box:
    #                     diag = {
    #                         "tried_paths": getattr(box, "tried_paths", []),
    #                         "config_path": getattr(box, "config_path", None),
    #                         "last_error": getattr(box, "last_error", ""),
    #                         "client_initialized": bool(getattr(box, "client", None)),
    #                         "user": getattr(box, "_user_identity", ""),
    #                     }
    #                 else:
    #                     diag = {"client_initialized": False, "last_error": "Box object not created"}
    #             except Exception as _e:
    #                 diag = {"client_initialized": bool(box and getattr(box, "client", None)), "last_error": str(_e)}
    #             if box and getattr(box, "client", None):
    #                 st.success(f"Authenticated to Box as {diag.get('user','')}\nConfig: {diag.get('config_path','')}")
    #             else:
    #                 st.error("Box initialization failed.")
    #             # Show diagnostics details
    #             st.write({
    #                 "config_path": diag.get("config_path"),
    #                 "tried_paths": diag.get("tried_paths"),
    #                 "client_initialized": diag.get("client_initialized"),
    #                 "last_error": diag.get("last_error"),
    #                 "BOX_JWT_JSON_present": bool(os.environ.get("BOX_JWT_JSON", "")),
    #             })
    #         except Exception as e:
    #             st.error(f"Box test failed: {e}")
    #             logger.error(f"Box test failed: {e}")
    
    # Test email button
    # if st.button("Create Test Email Draft"):
    #     try:
    #         # Mailbox settings (Graph)
    #         ex_cfg = get_section("exchange")
    #         to_addr = ex_cfg.get("username", "")
    #         cc_addr = ex_cfg.get("cc")
    #
    #         # Create a test email
    #         test_email = {
    #             "to": to_addr,
    #             "subject": "Test RFQ Email",
    #             "body": "<h1>Test Email</h1><p>This is a test email from the RFQ Sender application.</p>",
    #             "cc": [cc_addr] if cc_addr else [],
    #             "attachments": []
    #         }
    #
    #         # Create the test email draft
    #         if create_draft_email(
    #             recipient=test_email["to"],
    #             subject=test_email["subject"],
    #             body=test_email["body"],
    #         ):
    #             st.success("Test email draft created successfully in Outlook!")
    #             logger.info("Test email draft created successfully in Outlook")
    #         else:
    #             st.error("Failed to create test email draft.")
    #             logger.error("Failed to create test email draft")
    #
    #     except Exception as e:
    #         st.error(f"Error creating test email draft: {str(e)}")
    #         logger.error(f"Error creating test email draft: {str(e)}")


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