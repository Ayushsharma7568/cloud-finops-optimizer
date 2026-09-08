"""Tests for AWS EBS Discovery Service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from app.services.aws_ebs_discovery import discover_ebs_volumes
from app.services.aws_client import AWSCredentialsError, AWSConnectionError, AWSApiError

MOCK_EBS_RESPONSE = {
    'Volumes': [
        {
            'VolumeId': 'vol-11111111',
            'VolumeType': 'gp3',
            'Size': 100,
            'State': 'in-use',
            'AvailabilityZone': 'ap-south-1a',
            'CreateTime': datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
            'Encrypted': True,
            'Attachments': [
                {
                    'InstanceId': 'i-11111111',
                    'Device': '/dev/xvda'
                }
            ],
            'Tags': [
                {'Key': 'Name', 'Value': 'db-data-vol'}
            ]
        },
        {
            'VolumeId': 'vol-22222222',
            'VolumeType': 'gp2',
            'Size': 50,
            'State': 'available',  # Unattached
            'AvailabilityZone': 'ap-south-1b',
            'CreateTime': datetime(2023, 2, 1, 12, 0, tzinfo=timezone.utc),
            # Missing Encrypted (defaults False in boto if missing? usually explicitly returned, but good to test missing)
            # Missing Attachments
            # Missing Tags
        }
    ]
}

class TestAWSEBSDiscovery:

    @patch('app.services.aws_ebs_discovery.AWSClientFactory')
    def test_discover_ebs_volumes_success(self, mock_factory_class):
        """Test successful EBS discovery with normalization."""
        mock_factory = MagicMock()
        mock_factory.region = 'ap-south-1'
        mock_factory_class.return_value = mock_factory
        
        mock_ec2_client = MagicMock()
        mock_factory.get_client.return_value = mock_ec2_client
        
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [MOCK_EBS_RESPONSE]
        mock_ec2_client.get_paginator.return_value = mock_paginator
        
        volumes = discover_ebs_volumes()
        
        assert len(volumes) == 2
        
        # Check volume 1 (Attached)
        vol1 = volumes[0]
        assert vol1['resource_id'] == 'vol-11111111'
        assert vol1['resource_type'] == 'ebs_volume'
        assert vol1['state'] == 'in-use'
        assert vol1['metadata']['size_gb'] == 100
        assert vol1['metadata']['name'] == 'db-data-vol'
        assert vol1['metadata']['attached_instance_id'] == 'i-11111111'
        assert vol1['metadata']['device_name'] == '/dev/xvda'
        assert vol1['metadata']['encrypted'] is True
        
        # Check volume 2 (Unattached)
        vol2 = volumes[1]
        assert vol2['resource_id'] == 'vol-22222222'
        assert vol2['state'] == 'available'
        assert vol2['metadata']['name'] == 'Unknown'
        assert vol2['metadata']['attached_instance_id'] is None
        assert vol2['metadata']['encrypted'] is False

    @patch('app.services.aws_ebs_discovery.AWSClientFactory')
    def test_discover_ebs_empty_result(self, mock_factory_class):
        """Test discovery when no volumes exist."""
        mock_factory = MagicMock()
        mock_factory_class.return_value = mock_factory
        mock_ec2_client = MagicMock()
        mock_factory.get_client.return_value = mock_ec2_client
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'Volumes': []}]
        mock_ec2_client.get_paginator.return_value = mock_paginator
        
        volumes = discover_ebs_volumes()
        assert len(volumes) == 0

    @patch('app.services.aws_ebs_discovery.AWSClientFactory')
    def test_aws_api_error_handling(self, mock_factory_class):
        """Test proper wrapping of AWS errors."""
        mock_factory = MagicMock()
        mock_factory_class.return_value = mock_factory
        mock_ec2_client = MagicMock()
        mock_factory.get_client.return_value = mock_ec2_client
        
        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Internal server error'}}
        mock_ec2_client.get_paginator.side_effect = ClientError(error_response, 'DescribeVolumes')
        
        with pytest.raises(AWSApiError):
            discover_ebs_volumes()
