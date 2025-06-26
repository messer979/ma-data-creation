#!/usr/bin/env python3
"""
Simple runner for data import without Docker/Celery/Redis
Just runs the core data transfer functionality directly
"""

import sys
import os
from datetime import datetime

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.inventory_transfer_sync import run_transfer_sync

def main():
    """Run data transfer with example configuration"""
    
    # Example configuration - modify these values
    config = {
        'from_env': 'dtrev',  # without https:// and .sce.manh.com
        'from_org': '99005',
        'from_facility': '99005',
        'from_token': 'your_source_token_here',
        
        'to_env': 'dtres',   # without https:// and .sce.manh.com  
        'to_org': 'MANHD-005',
        'to_facility': 'MANHD-005',
        'to_token': 'your_target_token_here',
        
        'filter_type': 'Zone',  # Zone, Area, Aisle, etc.
        'filter_value': 'SC',   # The actual zone/area/aisle value
        'download_batch_size': 200,
        'upload_batch_size': 10
    }
    
    # Generate log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"transfer_status_{timestamp}.json"
    
    print("=" * 50)
    print("MA Data Creation Tool - Direct Transfer")
    print("=" * 50)
    print(f"Source: {config['from_env']} ({config['from_org']}/{config['from_facility']})")
    print(f"Target: {config['to_env']} ({config['to_org']}/{config['to_facility']})")
    print(f"Filter: {config['filter_type']} = {config['filter_value']}")
    print(f"Log file: {log_file}")
    print("=" * 50)
    
    def progress_callback(message):
        """Simple progress callback that prints to console"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    # Validate configuration
    if not all([
        config['from_token'] != 'your_source_token_here',
        config['to_token'] != 'your_target_token_here',
        config['filter_value']
    ]):
        print("❌ Error: Please update the configuration in this script with:")
        print("   - Valid source and target tokens")
        print("   - Filter value")
        print("   - Verify environment names and org/facility codes")
        return 1
    
    # Run the transfer
    try:
        print("🚀 Starting data transfer...")
        success = run_transfer_sync(config, log_file, progress_callback)
        
        if success:
            print("✅ Transfer completed successfully!")
            print(f"📝 Check log file: {log_file}")
            return 0
        else:
            print("❌ Transfer failed!")
            print(f"📝 Check log file for details: {log_file}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Transfer cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
