"""Tests for AWS EC2 Discovery Service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError

from app.services.aws_ec2_discovery import discover_ec2_instances
from app.services.aws_client import AWSCredentialsError, AWSConnectionError, AWSApiError

# Sample mock data for Boto3 paginator
MOCK_EC2_RESPONSE_PAGE_1 = {
    'Reservations': [
        {
            'Instances': [
                {
                    'InstanceId': 'i-11111111',
                    'InstanceType': 't3.micro',
                    'State': {'Name': 'running'},
                    'Placement': {'AvailabilityZone': 'ap-south-1a'},
                    'PrivateIpAddress': '10.0.0.5',
                    'PublicIpAddress': '203.0.113.5',
                    'LaunchTime': datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
                    'Tags': [
                        {'Key': 'Name', 'Value': 'web-server-1'},
                        {'Key': 'Environment', 'Value': 'production'}
                    ]
                }
            ]
        }
    ]
}

MOCK_EC2_RESPONSE_PAGE_2 = {
    'Reservations': [
        {
            'Instances': [
                {
                    'InstanceId': 'i-22222222',
                    'InstanceType': 't3.large',
                    'State': {'Name': 'stopped'},
                    'Placement': {'AvailabilityZone': 'ap-south-1b'},
                    'PrivateIpAddress': '10.0.0.6',
                    # No PublicIpAddress
                    'LaunchTime': datetime(2023, 2, 1, 12, 0, tzinfo=timezone.utc),
                    # No Tags
                }
            ]
        }
    ]
}


class TestAWSEC2Discovery:

    @patch('app.services.aws_ec2_discovery.AWSClientFactory')
    def test_discover_ec2_instances_success(self, mock_factory_class):
        """Test successful EC2 discovery with pagination and normalization."""
        mock_factory = MagicMock()
        mock_factory.region = 'ap-south-1'
        mock_factory_class.return_value = mock_factory
        
        mock_ec2_client = MagicMock()
        mock_factory.get_client.return_value = mock_ec2_client
        
        mock_paginator = MagicMock()
        # Simulate two pages of results
        mock_paginator.paginate.return_value = [MOCK_EC2_RESPONSE_PAGE_1, MOCK_EC2_RESPONSE_PAGE_2]
        mock_ec2_client.get_paginator.return_value = mock_paginator
        
        instances = discover_ec2_instances()
        
        assert len(instances) == 2
        
        # Check instance 1 (fully populated)
        inst1 = instances[0]
        assert inst1['resource_id'] == 'i-11111111'
        assert inst1['resource_type'] == 'ec2_instance'
        assert inst1['region'] == 'ap-south-1'
        assert inst1['state'] == 'running'
        assert inst1['metadata']['instance_type'] == 't3.micro'
        assert inst1['metadata']['name'] == 'web-server-1'
        assert inst1['metadata']['public_ip'] == '203.0.113.5'
        assert inst1['metadata']['tags']['Environment'] == 'production'
        
        # Check instance 2 (missing optional fields)
        inst2 = instances[1]
        assert inst2['resource_id'] == 'i-22222222'
        assert inst2['state'] == 'stopped'
        assert inst2['metadata']['name'] == 'Unknown'
        assert inst2['metadata']['public_ip'] is None
        assert inst2['metadata']['tags'] == {}

    @patch('app.services.aws_ec2_discovery.AWSClientFactory')
    def test_discover_ec2_empty_result(self, mock_factory_class):
        """Test discovery when no instances exist."""
        mock_factory = MagicMock()
        mock_factory_class.return_value = mock_factory
        
        mock_ec2_client = MagicMock()
        mock_factory.get_client.return_value = mock_ec2_client
        
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{'Reservations': []}]
        mock_ec2_client.get_paginator.return_value = mock_paginator
        
        instances = discover_ec2_instances()
        assert len(instances) == 0

    @patch('app.services.aws_ec2_discovery.AWSClientFactory')
    def test_aws_api_error_handling(self, mock_factory_class):
        """Test proper wrapping of AWS errors."""
        mock_factory = MagicMock()
        mock_factory_class.return_value = mock_factory
        
        mock_ec2_client = MagicMock()
        mock_factory.get_client.return_value = mock_ec2_client
        
        mock_ec2_client.get_paginator.side_effect = NoCredentialsError()
        with pytest.raises(AWSCredentialsError):
            discover_ec2_instances()
            
        mock_ec2_client.get_paginator.side_effect = EndpointConnectionError(endpoint_url="fake")
        with pytest.raises(AWSConnectionError):
            discover_ec2_instances()

        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}
        mock_ec2_client.get_paginator.side_effect = ClientError(error_response, 'DescribeInstances')
        with pytest.raises(AWSCredentialsError):
            discover_ec2_instances()
