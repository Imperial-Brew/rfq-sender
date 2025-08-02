import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import os
import logging
from datetime import datetime

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import utility functions
from utils.queue import load_queue, QUEUE_PATH
from utils.auth import get_user_role

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(parent_dir / "logs" / "view_queue.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_page():
    """Configure the page settings."""
    st.title("View RFQ Queue")
    st.markdown("""
    This page displays all parts currently in the RFQ queue.
    You can filter and sort the queue to find specific entries.
    """)

def display_queue_data(user, role):
    """Display the queue data with filtering options."""
    try:
        # Debug: Show the queue path
        st.sidebar.write(f"Queue path: {QUEUE_PATH}")
        
        # Load queue data
        df = load_queue(QUEUE_PATH)
        
        # Debug: Show if file exists
        st.sidebar.write(f"Queue file exists: {os.path.exists(QUEUE_PATH)}")
        
        # Debug: Show dataframe info
        if not df.empty:
            st.sidebar.write(f"Queue data loaded: {len(df)} rows")
            st.sidebar.write(f"Columns: {df.columns.tolist()}")
        else:
            st.sidebar.write("Queue dataframe is empty")
            st.info("The queue is currently empty. Add parts using the 'Add to Queue' page.")
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
        
        if part_filter:
            filtered_df = filtered_df[filtered_df["part_number"].str.contains(part_filter, case=False)]
        
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
                            if pd.isna(x) or x is pd.NaT:
                                return "No Date"
                            
                            date_val = x.date() if hasattr(x, 'date') else None
                            if date_val is None:
                                return "No Date"
                                
                            return "Overdue" if date_val < today else "Active"
                        except Exception as e:
                            logger.debug(f"Error comparing date value {x}: {str(e)}")
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
        
        # Reorder and select columns for display
        columns_to_display = ["part_number", "process", "spec", "quantities"]
        if "priority" in display_df.columns:
            columns_to_display.append("priority")
        if "due_date" in display_df.columns:
            columns_to_display.append("due_date")
        if "status" in display_df.columns:
            columns_to_display.append("status")
        if "submitted_by" in display_df.columns:
            columns_to_display.append("submitted_by")
        
        # Only include columns that actually exist in the dataframe
        columns_to_display = [col for col in columns_to_display if col in display_df.columns]
        
        # Display the dataframe
        st.dataframe(
            display_df[columns_to_display],
            use_container_width=True,
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
    
    # Display queue data
    display_queue_data(user, role)

if __name__ == "__main__":
    main()