"""Local verification script for AWS Database Integration.

Safely synchronizes AWS resources into the local PostgreSQL database using
the configured AWS credentials.
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path so we can import app modules
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from app import create_app
from app.services.aws_ingestion import sync_aws_resources

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("=" * 50)
    print("AWS to PostgreSQL Sync Verification")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        try:
            results = sync_aws_resources()
            print("\nSync Results:")
            print(f"  - EC2 Instances Processed: {results['ec2_instances_processed']}")
            print(f"  - EBS Volumes Processed:   {results['ebs_volumes_processed']}")
            
            if results["errors"]:
                print("\nErrors encountered during sync:")
                for error in results["errors"]:
                    print(f"  - {error}")
            else:
                print("\nSync completed successfully without errors.")
                
        except Exception as e:
            logger.error(f"\nUnexpected error during synchronization: {e}")

if __name__ == "__main__":
    main()
