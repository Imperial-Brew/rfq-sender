"""
Test script to verify the bug tracker page is accessible.

This script checks if the bug tracker page is properly configured and accessible.
"""
import os
import sys
import importlib.util
from pathlib import Path

# Add the project root to the Python path (adjusted for new location in tests/bug_tracker/)
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def test_bug_tracker_exists():
    """Test if the bug tracker page file exists."""
    bug_tracker_path = project_root / "streamlit_app" / "pages" / "04_bug_tracker.py"
    assert bug_tracker_path.exists(), f"Bug tracker file not found at {bug_tracker_path}"
    print(f"✓ Bug tracker file exists at {bug_tracker_path}")

def test_db_module_exists():
    """Test if the database module used by the bug tracker exists."""
    db_path = project_root / "streamlit_app" / "utils" / "db.py"
    assert db_path.exists(), f"Database module not found at {db_path}"
    print(f"✓ Database module exists at {db_path}")

def test_bug_tracker_imports():
    """Test if the bug tracker page can be imported without errors."""
    try:
        # Check if streamlit is installed
        try:
            import streamlit
            streamlit_installed = True
        except ImportError:
            streamlit_installed = False
            print("ℹ Streamlit not installed in this environment, skipping import test")
            return
        
        # Import the bug tracker module
        spec = importlib.util.spec_from_file_location(
            "bug_tracker", 
            str(project_root / "streamlit_app" / "pages" / "04_bug_tracker.py")
        )
        bug_tracker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bug_tracker)
        
        print("✓ Bug tracker module imported successfully")
    except Exception as e:
        print(f"✗ Error importing bug tracker module: {str(e)}")
        if streamlit_installed:
            raise  # Only raise if streamlit is installed

def test_batch_script_exists():
    """Test if the batch script to run the streamlit app exists."""
    batch_script_path = project_root / "Start_streamlit_app.bat"
    assert batch_script_path.exists(), f"Batch script not found at {batch_script_path}"
    print(f"✓ Batch script exists at {batch_script_path}")

def test_documentation_exists():
    """Test if the bug tracker documentation exists."""
    doc_path = project_root / "docs" / "bug_tracker.md"
    assert doc_path.exists(), f"Documentation not found at {doc_path}"
    print(f"✓ Documentation exists at {doc_path}")

def run_tests():
    """Run all tests."""
    print("Testing bug tracker configuration...")
    test_bug_tracker_exists()
    test_db_module_exists()
    test_bug_tracker_imports()
    test_batch_script_exists()
    test_documentation_exists()
    print("\nAll tests passed! The bug tracker is properly configured.")
    print("\nTo access the bug tracker, run the following command:")
    print("    streamlit run streamlit_app/app.py")
    print("Or use the batch script:")
    print("    Start_streamlit_app.bat")

if __name__ == "__main__":
    run_tests()