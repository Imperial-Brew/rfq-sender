"""
Test script to verify queue loading functionality.

This script tests loading the queue data to ensure it works correctly
without any 'part_number' field errors.
"""

import pandas as pd
import os
import sys
from pathlib import Path

# Add the parent directory to the path (adjusted for new location in tests/queue/)
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import the logging module
from utils.rfq_logging import get_logger

# Get module-specific logger
logger = get_logger(__name__)

def test_queue_loading():
    """Test loading the queue data directly and through utils.queue."""
    try:
        # 1. Test direct loading of queue.csv
        queue_path = os.path.join(parent_dir, "docs", "queue.csv")
        logger.info(f"Testing direct loading of queue from {queue_path}")
        
        if not os.path.exists(queue_path):
            logger.error(f"Queue file not found at {queue_path}")
            return False
        
        # Load the CSV file directly
        df_direct = pd.read_csv(queue_path)
        logger.info(f"Successfully loaded queue directly with {len(df_direct)} entries")
        
        # Print column names to verify
        logger.info(f"Queue columns: {df_direct.columns.tolist()}")
        
        # 2. Test loading through utils.queue
        logger.info("Testing loading through utils.rfq_queue.load_queue")
        from utils.rfq_queue import load_queue, QUEUE_PATH
        
        df_util = load_queue(QUEUE_PATH)
        logger.info(f"Successfully loaded queue through utils with {len(df_util)} entries")
        
        # 3. Test accessing Part_Number column (should work)
        if 'Part_Number' in df_direct.columns:
            logger.info("Part_Number column exists in direct loading")
            # Try to access the first Part_Number value
            if not df_direct.empty:
                first_part = df_direct['Part_Number'].iloc[0]
                logger.info(f"First Part_Number: {first_part}")
        else:
            logger.warning("Part_Number column not found in direct loading")
        
        # 4. Test accessing part_number column (should work after standardization in load_queue)
        if 'part_number' in df_util.columns:
            logger.info("part_number column exists after standardization")
            # Try to access the first part_number value
            if not df_util.empty:
                first_part = df_util['part_number'].iloc[0]
                logger.info(f"First part_number: {first_part}")
        else:
            logger.warning("part_number column not found after standardization")
            # Print all columns to see what's available
            logger.info(f"Available columns after standardization: {df_util.columns.tolist()}")
        
        # 5. Test the app.py scenario
        logger.info("Testing the app.py scenario (just counting rows)")
        try:
            # Just load the queue file directly without accessing specific columns
            queue_df = pd.read_csv(queue_path)
            count = len(queue_df)
            logger.info(f"Queue Items count: {count}")
        except Exception as e:
            logger.error(f"Error in app.py scenario: {str(e)}")
            return False
        
        logger.info("All queue loading tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error in test_queue_loading: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_queue_loading()
    if success:
        print("Queue loading tests completed successfully!")
    else:
        print("Queue loading tests failed. Check the logs for details.")