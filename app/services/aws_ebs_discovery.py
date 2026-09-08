"""AWS EBS Discovery Service.

Discovers and normalizes EBS volumes using the Boto3 AWSClientFactory.
"""

import logging
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError
from app.services.aws_client import (
    AWSClientFactory,
    AWSCredentialsError,
    AWSConnectionError,
    AWSApiError
)

logger = logging.getLogger(__name__)


def discover_ebs_volumes() -> list[dict]:
    """Discover all EBS volumes in the configured region.
    
    Handles pagination to ensure all volumes are returned.
    Normalizes the raw AWS volume data into a consistent dictionary structure.
    
    Returns:
        List of normalized EBS volume dictionaries.
        
    Raises:
        AWSCredentialsError, AWSConnectionError, AWSApiError
    """
    factory = AWSClientFactory()
    
    try:
        ec2_client = factory.get_client('ec2')
        paginator = ec2_client.get_paginator('describe_volumes')
        
        discovered_volumes = []
        
        for page in paginator.paginate():
            for volume in page.get('Volumes', []):
                normalized = _normalize_ebs_volume(volume, factory.region)
                discovered_volumes.append(normalized)
                    
        logger.info("Discovered %d EBS volumes.", len(discovered_volumes))
        return discovered_volumes

    except NoCredentialsError:
        raise AWSCredentialsError("No AWS credentials found.")
    except EndpointConnectionError as e:
        raise AWSConnectionError(f"Could not connect to AWS endpoints: {e}")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code in ['AuthFailure', 'UnauthorizedOperation', 'AccessDenied']:
            raise AWSCredentialsError(f"AWS credentials rejected or lacking permissions ({error_code}).")
        raise AWSApiError(f"AWS API Error: {e}")
    except Exception as e:
        raise AWSApiError(f"Unexpected error during EBS discovery: {e}")


def _normalize_ebs_volume(volume: dict, region: str) -> dict:
    """Normalize raw Boto3 EBS volume dictionary.
    
    Safely extracts optional fields.
    """
    # Extract tags into a simple dict and find the Name tag
    tags_dict = {}
    name_tag = "Unknown"
    for tag in volume.get('Tags', []):
        key = tag.get('Key')
        value = tag.get('Value')
        tags_dict[key] = value
        if key == 'Name':
            name_tag = value
            
    # Handle attachments
    attachments = volume.get('Attachments', [])
    attached_instance_id = None
    device_name = None
    if attachments:
        # Assuming we just take the first attachment
        attached_instance_id = attachments[0].get('InstanceId')
        device_name = attachments[0].get('Device')

    return {
        "resource_id": volume.get('VolumeId'),
        "resource_type": "ebs_volume",
        "region": region,
        "state": volume.get('State', 'unknown'),
        "metadata": {
            "volume_type": volume.get('VolumeType'),
            "size_gb": volume.get('Size'),
            "availability_zone": volume.get('AvailabilityZone'),
            "create_time": volume.get('CreateTime').isoformat() if volume.get('CreateTime') else None,
            "encrypted": volume.get('Encrypted', False),
            "attached_instance_id": attached_instance_id,
            "device_name": device_name,
            "name": name_tag,
            "tags": tags_dict
        }
    }
