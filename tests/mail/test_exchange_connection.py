"""
Test script to verify Exchange connection with updated SSL verification settings.
"""
import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from other modules
# Updated for new location in tests/email/
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the necessary modules
from core.config import init_config

# Initialize configuration
init_config()

def test_exchange_connection():
    """Deprecated test: EWS/Exchange paths removed. Skipping.
    This test is retained for history but no longer exercises any code.
    """
    logger.info("Skipping legacy Exchange connection test (Graph-only backend now).")
    assert True
    return True

if __name__ == "__main__":
    logger.info("Starting Exchange connection test script")
    success = test_exchange_connection()
    if success:
        logger.info("Test completed successfully")
    else:
        logger.error("Test failed")