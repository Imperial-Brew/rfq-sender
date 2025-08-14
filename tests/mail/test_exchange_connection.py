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
from core.config import ExchangeConfig, init_config
from utils.rfq_email import initialize_exchange

# Initialize configuration
init_config()

def test_exchange_connection():
    """Test the Exchange connection with updated SSL verification settings."""
    logger.info("Starting Exchange connection test")
    
    try:
        # Get email settings from ExchangeConfig
        exchange_settings = {
            "server": ExchangeConfig.get_server(),
            "username": ExchangeConfig.get_username(),
            "password": ExchangeConfig.get_password(),
            "from_email": ExchangeConfig.get_from_email(),
            "cc": ExchangeConfig.get_cc_email()
        }
        
        # Initialize Exchange connection
        logger.info("Initializing Exchange connection")
        account = initialize_exchange(exchange_settings)
        
        # Test if the connection was successful
        if account:
            logger.info("Exchange connection successful!")
            logger.info(f"Connected to account: {account.primary_smtp_address}")
            logger.info(f"Drafts folder: {account.drafts.name}")
            return True
        else:
            logger.error("Exchange connection failed")
            return False
    except Exception as e:
        logger.error(f"Error testing Exchange connection: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Exchange connection test script")
    success = test_exchange_connection()
    if success:
        logger.info("Test completed successfully")
    else:
        logger.error("Test failed")