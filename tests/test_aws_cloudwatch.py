import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError, EndpointConnectionError
from app.services.aws_cloudwatch import CloudWatchService
from app.services.aws_client import AWSApiError, AWSConnectionError

@pytest.fixture
def mock_client_factory():
    factory = MagicMock()
    factory.get_client.return_value = MagicMock()
    return factory

@pytest.fixture
def cloudwatch_service(mock_client_factory):
    return CloudWatchService(client_factory=mock_client_factory)

def test_get_ec2_cpu_utilization_success(cloudwatch_service):
    # Mock response with multiple datapoints
    mock_response = {
        'Datapoints': [
            {'Average': 10.0, 'Unit': 'Percent'},
            {'Average': 20.0, 'Unit': 'Percent'}
        ]
    }
    cloudwatch_service.client.get_metric_statistics.return_value = mock_response

    result = cloudwatch_service.get_ec2_cpu_utilization('i-1234567890abcdef0')

    assert result['resource_id'] == 'i-1234567890abcdef0'
    assert result['metric_name'] == 'CPUUtilization'
    assert result['average_cpu'] == 15.0
    assert result['datapoint_count'] == 2
    assert result['unit'] == 'Percent'
    assert 'start_time' in result
    assert 'end_time' in result

def test_get_ec2_cpu_utilization_empty_datapoints(cloudwatch_service):
    # Mock response with empty datapoints
    mock_response = {
        'Datapoints': []
    }
    cloudwatch_service.client.get_metric_statistics.return_value = mock_response

    result = cloudwatch_service.get_ec2_cpu_utilization('i-1234567890abcdef0')

    assert result['resource_id'] == 'i-1234567890abcdef0'
    assert result['metric_name'] == 'CPUUtilization'
    assert result['average_cpu'] is None
    assert result['datapoint_count'] == 0
    assert result['unit'] == 'Percent'

def test_get_ec2_cpu_utilization_api_error(cloudwatch_service):
    error_response = {'Error': {'Code': 'InternalError', 'Message': 'Something went wrong'}}
    cloudwatch_service.client.get_metric_statistics.side_effect = ClientError(error_response, 'GetMetricStatistics')

    with pytest.raises(AWSApiError):
        cloudwatch_service.get_ec2_cpu_utilization('i-1234567890abcdef0')

def test_get_ec2_cpu_utilization_connection_error(cloudwatch_service):
    cloudwatch_service.client.get_metric_statistics.side_effect = EndpointConnectionError(endpoint_url='https://monitoring.aws.com')

    with pytest.raises(AWSConnectionError):
        cloudwatch_service.get_ec2_cpu_utilization('i-1234567890abcdef0')

def test_get_ec2_cpu_utilization_client_creation_error():
    factory = MagicMock()
    factory.get_client.side_effect = Exception("Failed to create client")
    
    with pytest.raises(Exception):
        CloudWatchService(client_factory=factory)

def test_get_ec2_cpu_utilization_arguments(cloudwatch_service):
    mock_response = {'Datapoints': []}
    cloudwatch_service.client.get_metric_statistics.return_value = mock_response

    cloudwatch_service.get_ec2_cpu_utilization('i-1234567890abcdef0', days=7, period=3600)

    call_kwargs = cloudwatch_service.client.get_metric_statistics.call_args.kwargs
    assert call_kwargs['Namespace'] == 'AWS/EC2'
    assert call_kwargs['MetricName'] == 'CPUUtilization'
    assert call_kwargs['Dimensions'] == [{'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}]
    assert call_kwargs['Period'] == 3600
    assert call_kwargs['Statistics'] == ['Average']
    # Check time delta is roughly 7 days
    delta = call_kwargs['EndTime'] - call_kwargs['StartTime']
    assert abs(delta.days - 7) == 0
