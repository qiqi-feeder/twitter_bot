
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import logger
from get_data.main import run_once

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting manual test of Auto-Post...")
    print("This script will trigger the 'run_once' function.")
    print("Check the Web UI History to see the result.")
    print("-" * 50)
    
    try:
        run_once()
        print("-" * 50)
        print("✅ Execution completed.")
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        logger.error(f"Manual test failed: {e}")

if __name__ == "__main__":
    main()
