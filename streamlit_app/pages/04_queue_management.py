import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import os
import logging
from datetime import datetime

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import configuration and utility functions
from core.config import Paths, LoggingConfig, init_config
from utils.specs import load_process_list, load_specs_for_process
from utils.rfq_queue import add_to_queue, load_queue, save_queue, _get_box_store, _standardize_df
from streamlit_app.utils.auth_shim import get_user_role
from streamlit_app.utils.auth_middleware import require_authentication
from utils.rfq_logging import get_logger

if not require_authentication():
    st.stop()

# Initialize configuration
init_config()

# Set up logging using the centralized configuration
logger = get_logger(__name__)

def setup_page():
    """Configure the page settings."""
    st.title("Queue Management")
    st.markdown("""
    This page allows you to add new parts to the RFQ queue and view the current queue contents.
    Use the tabs below to switch between adding parts and viewing the queue.
    """)

def display_add_to_queue_form(user):
    """Display the form for adding a part to the queue."""
    processes = load_process_list()
    
    # Process selection outside the form
    st.subheader("Select Process and Spec")
    selected_process = st.selectbox(
        "Process", 
        options=sorted(processes), 
        help="Select the manufacturing process"
    )
    
    # Load specs based on selected process (guard against None/empty)
    if selected_process:
        available_specs = load_specs_for_process(selected_process)
    else:
        available_specs = []
    spec = st.selectbox(
        "Spec (optional)", 
        options=available_specs, 
        help="Select the specification if applicable"
    )
    
    st.subheader("Part Details")
    with st.form("rfq_form"):
        col1, col2 = st.columns(2)

        with col1:
            part_number = st.text_input("Part Number", help="Enter the part number to be quoted")
            rev = st.text_input("Rev", help="Enter drawing revision (e.g., A, B, C)")
            callout = st.text_input("Callout", help="Enter the callout text from the drawing")

        with col2:
            material = st.text_input("Material", help="Enter the material specification")
            material_family = st.text_input("Material Family", help="Enter the material family (e.g., Aluminum, Steel)")
            quantity = st.text_input(
                "Quantities (comma separated)", 
                value="1,5,10",
                help="Enter quantities separated by commas"
            )
        
        file_location = st.text_input(
            "File Location", 
            help="Enter the location of the files to be quoted"
        )
        
        # New fields: Quote/Sales Order # and ITAR/CUI flag
        qt_so = st.text_input(
            "Quote/Sales Order # (qt/so #)",
            help="Enter the quote or sales order identifier (e.g., QT57267 or SO12345)"
        )
        cui_itar_flag = st.checkbox(
            "Contains ITAR/CUI",
            help="Check if the RFQ contains ITAR/CUI sensitive information"
        )
        
        notes = st.text_area(
            "Notes", 
            help="Enter any additional notes or instructions"
        )
        
        submitted = st.form_submit_button("Add to Queue", width="stretch")
        
        if submitted:
            if not part_number or not selected_process:
                st.warning("Part number and process are required.")
                logger.warning(f"Submission failed: missing required fields")
            else:
                try:
                    add_to_queue({
                        "part_number": part_number.strip(),
                        "rev": rev.strip(),
                        "callout": callout.strip(),
                        "process": selected_process.strip(),
                        "spec": spec.strip(),
                        "material": material.strip(),
                        "material_family": material_family.strip(),
                        "quantities": quantity.strip(),
                        "file_location": file_location.strip(),
                        "notes": notes.strip(),
                        "submitted_by": user["name"],
                        "qt/so #": qt_so.strip(),
                        "cui_itar": "TRUE" if cui_itar_flag else "FALSE",
                    })
                    st.success("✅ Part added to queue!")
                    logger.info(f"Part {part_number} added to queue by {user['name']}")
                    
                    # Clear form (requires rerun)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding part to queue: {str(e)}")
                    logger.error(f"Error adding part to queue: {str(e)}")

def display_queue_data(user, role):
    """Display the queue data with filtering options."""
    try:
        # Load queue data
        df = load_queue()
        
        if df.empty:
            st.info("The queue is currently empty. Add parts using the 'Add to Queue' tab.")
            return
        
        # Add filter options
        st.subheader("Filter Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filter by part number
            part_filter = st.text_input("Filter by Part Number", "")
        
        with col2:
            # Filter by process
            if "process" in df.columns:
                processes = ["All"] + sorted(df["process"].unique().tolist())
                process_filter = st.selectbox("Filter by Process", processes)
            else:
                process_filter = "All"
        
        with col3:
            # Filter by expedited status
            if "expedited" in df.columns:
                expedited_filter = st.selectbox(
                    "Expedited Status", 
                    ["All", "Expedited Only", "Standard Only"]
                )
            else:
                expedited_filter = "All"
        
        # Apply filters
        filtered_df = df.copy()
        
        if part_filter and "part_number" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["part_number"].astype(str).str.contains(part_filter, case=False)]
        
        if process_filter != "All" and "process" in df.columns:
            filtered_df = filtered_df[filtered_df["process"] == process_filter]
        
        if expedited_filter != "All" and "expedited" in df.columns:
            if expedited_filter == "Expedited Only":
                filtered_df = filtered_df[filtered_df["expedited"] == True]
            elif expedited_filter == "Standard Only":
                filtered_df = filtered_df[filtered_df["expedited"] == False]
        
        # Display the filtered queue
        st.subheader("Queue Contents")
        
        if filtered_df.empty:
            st.warning("No entries match the selected filters.")
            return
        
        # Format the dataframe for display
        display_df = filtered_df.copy()
        
        # Convert date columns to datetime if they exist
        if "due_date" in display_df.columns:
            try:
                # First convert to datetime with error handling
                display_df["due_date"] = pd.to_datetime(display_df["due_date"], errors="coerce")
                
                # Create a temporary column for date comparison
                try:
                    # Add a status column based on due date
                    today = datetime.now().date()
                    
                    # Define a safe date comparison function
                    def safe_date_compare(x):
                        try:
                            # Handle NaN, NaT, None, or any non-datetime value
                            if pd.isna(x) or x is pd.NaT or x is None:
                                return "No Date"
                            
                            # Ensure x is a datetime object
                            if not isinstance(x, (pd.Timestamp, datetime)):
                                # If it's a string or other type, return "No Date"
                                return "No Date"
                            
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
                    display_df["status"] = display_df["due_date"].apply(safe_date_compare)
                    
                    # Format dates for display after comparison is done
                    display_df["due_date"] = display_df["due_date"].dt.strftime("%Y-%m-%d")
                except Exception as e:
                    logger.warning(f"Error calculating status from dates: {str(e)}")
                    # If there's an error, just don't add the status column
                    if "status" in display_df.columns:
                        del display_df["status"]
            except Exception as e:
                logger.warning(f"Error processing due dates: {str(e)}")
                # If there's an error, just don't add the status column
                if "status" in display_df.columns:
                    del display_df["status"]
        
        # Highlight expedited items
        if "expedited" in display_df.columns:
            display_df["priority"] = display_df["expedited"].apply(
                lambda x: "⚠️ Expedited" if x else "Standard"
            )
        
        # Hide legacy RFQ # column if present
        display_df = display_df.drop(columns=["rfq #", "RFQ #"], errors="ignore")

        # Use all columns from the dataframe (after dropping legacy columns)
        columns_to_display = display_df.columns.tolist()

        # Ensure important columns appear first if they exist
        preferred_order = [
            "part_number", "rev", "process", "spec", "quantities",
            "priority", "due_date", "status", "submitted_by"
        ]
        for col in reversed(preferred_order):
            if col in columns_to_display:
                columns_to_display.remove(col)
                columns_to_display.insert(0, col)
        
        # Display the dataframe
        st.dataframe(
            display_df[columns_to_display],
            width="stretch",
            hide_index=True
        )
        
        # Add export option
        if st.button("Export Queue to CSV"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="rfq_queue_export.csv",
                mime="text/csv"
            )

        # Queue Management Tools (moved from Page 3)
        with st.expander("Queue Management Tools", expanded=False):
            # Duplicate handling policy for RFQ Master logging (kept for parity)
            dup_policy_label = "When logging to RFQ Master, if a matching entry already exists (same qt/so #, part, process, vendor, contact):"
            dup_choice = st.radio(
                dup_policy_label,
                options=[
                    "Skip (do not add new line)",
                    "Update (status/notes/link/date)",
                    "Append (always add new line)",
                ],
                index=0,
                key="rfq_master_dup_policy_page1",
                help=(
                    "Skip: return existing rfq# and do not write.\n"
                    "Update: update status/notes/rfq_folder/date on the existing line.\n"
                    "Append: always add a new row even if a match exists."
                ),
            )
            _on_dup_map = {
                "Skip (do not add new line)": "skip",
                "Update (status/notes/link/date)": "update",
                "Append (always add new line)": "append",
            }
            on_duplicate_policy = _on_dup_map.get(dup_choice, "skip")

            # Refresh queue from Box
            if st.button("Refresh queue from Box", key="refresh_from_box_page1"):
                try:
                    with st.spinner("Refreshing queue from Box..."):
                        store = _get_box_store()
                        if store is None:
                            st.error(
                                "Box is not configured or failed to initialize; cannot refresh from Box.\n"
                                "Check BOX_QUEUE_FILE_ID / BOX_QUEUE_FOLDER_ID and Box credentials."
                            )
                        else:
                            refreshed_df = store.load_df()
                            refreshed_df = _standardize_df(refreshed_df)
                            st.success(f"Loaded {len(refreshed_df)} row(s) from Box and refreshed the queue in the UI.")
                            st.dataframe(refreshed_df, width="stretch", hide_index=True)

                            if st.button("Save cleaned queue back to Box (drop legacy columns)", key="save_cleaned_queue_box_page1"):
                                try:
                                    save_queue(refreshed_df)
                                    st.success("Cleaned queue saved back to Box. Legacy columns have been dropped.")
                                except Exception as _e:
                                    st.error(f"Failed to save cleaned queue back to Box: {_e}")
                                    logger.error(f"Failed to save cleaned queue back to Box: {_e}")
                except Exception as e:
                    st.error(f"Refresh from Box failed: {e}")
                    logger.exception("Refresh from Box failed")

            # Validate process/spec against familiar list
            try:
                from streamlit_app.utils.vendor_helpers import build_familiarity_report
                if st.button("Validate process/spec against familiar list", key="validate_familiarity_page1"):
                    report_df = build_familiarity_report(df)
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
                            key="download_unfamiliar_report_page1",
                        )
            except Exception as e:
                st.error(f"Error running familiarity validation: {e}")
                logger.exception("Error running familiarity validation")
        
        # Log the view
        logger.info(f"Queue viewed by {user['name']} with {len(filtered_df)} entries after filtering")
        
    except Exception as e:
        st.error(f"Error loading queue data: {str(e)}")
        logger.error(f"Error loading queue data: {str(e)}")

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
    
    # Create tabs for View Queue and Add to Queue (View is default)
    view_tab, add_tab = st.tabs(["View Queue", "Add to Queue"])
    
    with view_tab:
        display_queue_data(user, role)
    
    with add_tab:
        display_add_to_queue_form(user)

if __name__ == "__main__":
    main()