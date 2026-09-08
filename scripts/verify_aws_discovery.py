"""Local verification script for AWS Discovery.

Safely tests EC2 and EBS discovery using locally configured credentials.
Does NOT modify AWS resources or persist data to the database.
"""

import sys
import json
import logging
from pathlib import Path

# Add project root to Python path so we can import app modules
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from app.services.aws_ec2_discovery import discover_ec2_instances
from app.services.aws_ebs_discovery import discover_ebs_volumes
from app.services.aws_client import AWSCredentialsError, AWSConnectionError, AWSApiError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("=" * 50)
    print("AWS Resource Discovery Verification")
    print("=" * 50)
    
    try:
        # EC2 Discovery
        print("\n--- Discovering EC2 Instances ---")
        instances = discover_ec2_instances()
        print(f"Found {len(instances)} EC2 instances:")
        for inst in instances:
            print(f"  - {inst['resource_id']} ({inst['state']}) | Type: {inst['metadata'].get('instance_type')} | Name: {inst['metadata'].get('name')}")
            
        # EBS Discovery
        print("\n--- Discovering EBS Volumes ---")
        volumes = discover_ebs_volumes()
        print(f"Found {len(volumes)} EBS volumes:")
        for vol in volumes:
            attachment = f"Attached to {vol['metadata']['attached_instance_id']}" if vol['metadata'].get('attached_instance_id') else "Unattached"
            print(f"  - {vol['resource_id']} ({vol['state']}) | Size: {vol['metadata'].get('size_gb')}GB | {attachment} | Name: {vol['metadata'].get('name')}")

        print("\nDiscovery completed successfully.")
        print("Note: These resources were NOT saved to the database.")
        
    except (AWSCredentialsError, AWSConnectionError, AWSApiError) as e:
        logger.error(f"\nDiscovery Failed: {e}")
        logger.info("Please ensure your AWS credentials are properly configured.")
    except Exception as e:
        logger.error(f"\nUnexpected error during verification: {e}")

if __name__ == "__main__":
    main()
