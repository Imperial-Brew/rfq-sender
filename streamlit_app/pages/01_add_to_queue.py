import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import logging

# Add the parent directory to the path so we can import from other modules
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import utility functions
from utils.specs import load_process_list, load_specs_for_process
from utils.queue import add_to_queue, QUEUE_PATH
from utils.auth import get_user_role

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(parent_dir / "logs" / "add_to_queue.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_page():
    """Configure the page settings."""
    st.title("Add to RFQ Queue")
    st.markdown("""
    Use this form to add a new part to the RFQ queue. 
    Fill in the required information and click "Add to Queue" to submit.
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
    
    # Load specs based on selected process
    available_specs = load_specs_for_process(selected_process)
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
        
        notes = st.text_area(
            "Notes", 
            help="Enter any additional notes or instructions"
        )
        
        submitted = st.form_submit_button("Add to Queue", use_container_width=True)
        
        if submitted:
            if not part_number or not selected_process:
                st.warning("Part number and process are required.")
                logger.warning(f"Submission failed: missing required fields")
            else:
                try:
                    add_to_queue(QUEUE_PATH, {
                        "part_number": part_number.strip(),
                        "callout": callout.strip(),
                        "process": selected_process.strip(),
                        "spec": spec.strip(),
                        "material": material.strip(),
                        "material_family": material_family.strip(),
                        "quantities": quantity.strip(),
                        "file_location": file_location.strip(),
                        "notes": notes.strip(),
                        "submitted_by": user["name"]
                    })
                    st.success("✅ Part added to queue!")
                    logger.info(f"Part {part_number} added to queue by {user['name']}")
                    
                    # Clear form (requires rerun)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding part to queue: {str(e)}")
                    logger.error(f"Error adding part to queue: {str(e)}")

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
    
    # Display form
    display_add_to_queue_form(user)

if __name__ == "__main__":
    main()