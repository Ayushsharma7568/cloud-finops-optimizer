"""AWS EC2 Discovery Service.

Discovers and normalizes EC2 instances using the Boto3 AWSClientFactory.
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


def discover_ec2_instances() -> list[dict]:
    """Discover all EC2 instances in the configured region.
    
    Handles pagination to ensure all instances are returned.
    Normalizes the raw AWS instance data into a consistent dictionary structure.
    
    Returns:
        List of normalized EC2 instance dictionaries.
        
    Raises:
        AWSCredentialsError, AWSConnectionError, AWSApiError
    """
    factory = AWSClientFactory()
    
    try:
        ec2_client = factory.get_client('ec2')
        paginator = ec2_client.get_paginator('describe_instances')
        
        discovered_instances = []
        
        for page in paginator.paginate():
            for reservation in page.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    normalized = _normalize_ec2_instance(instance, factory.region)
                    discovered_instances.append(normalized)
                    
        logger.info("Discovered %d EC2 instances.", len(discovered_instances))
        return discovered_instances

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
        raise AWSApiError(f"Unexpected error during EC2 discovery: {e}")


def _normalize_ec2_instance(instance: dict, region: str) -> dict:
    """Normalize raw Boto3 EC2 instance dictionary.
    
    Safely extracts optional fields.
    """
    # Extract tags into a simple dict and find the Name tag
    tags_dict = {}
    name_tag = "Unknown"
    for tag in instance.get('Tags', []):
        key = tag.get('Key')
        value = tag.get('Value')
        tags_dict[key] = value
        if key == 'Name':
            name_tag = value

    return {
        "resource_id": instance.get('InstanceId'),
        "resource_type": "ec2_instance",
        "region": region,
        "state": instance.get('State', {}).get('Name', 'unknown'),
        "metadata": {
            "instance_type": instance.get('InstanceType'),
            "availability_zone": instance.get('Placement', {}).get('AvailabilityZone'),
            "launch_time": instance.get('LaunchTime').isoformat() if instance.get('LaunchTime') else None,
            "private_ip": instance.get('PrivateIpAddress'),
            "public_ip": instance.get('PublicIpAddress'),
            "name": name_tag,
            "tags": tags_dict
        }
    }
