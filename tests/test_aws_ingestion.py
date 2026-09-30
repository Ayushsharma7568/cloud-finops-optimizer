"""Tests for the AWS Database Ingestion Service."""

import pytest
from unittest.mock import patch, MagicMock
from app.services.aws_ingestion import sync_aws_resources, sync_aws_costs, _ingest_resource
from app.services.aws_client import AWSApiError

# Sample normalized data as it would be returned from discovery
MOCK_EC2_DATA = {
    "resource_id": "i-test1",
    "resource_type": "ec2_instance",
    "region": "ap-south-1",
    "state": "running",
    "metadata": {
        "instance_type": "t3.micro",
        "name": "test-ec2",
        "public_ip": "1.1.1.1",
        "tags": {}
    }
}

MOCK_EBS_DATA = {
    "resource_id": "vol-test1",
    "resource_type": "ebs_volume",
    "region": "ap-south-1",
    "state": "in-use",
    "metadata": {
        "size_gb": 100,
        "name": "test-ebs",
        "attached_instance_id": "i-test1",
        "encrypted": True,
        "tags": {}
    }
}

class TestAWSIngestion:

    @patch('app.services.aws_ingestion.sync_aws_costs')
    @patch('app.services.aws_ingestion.discover_ec2_instances')
    @patch('app.services.aws_ingestion.discover_ebs_volumes')
    @patch('app.services.aws_ingestion.ResourceRepository.upsert_resource')
    def test_sync_aws_resources_success(self, mock_upsert, mock_discover_ebs, mock_discover_ec2, mock_sync_costs):
        """Test successful synchronization of EC2 and EBS resources."""
        mock_discover_ec2.return_value = [MOCK_EC2_DATA]
        mock_discover_ebs.return_value = [MOCK_EBS_DATA]
        mock_sync_costs.return_value = [MagicMock()]
        
        results = sync_aws_resources()
        
        assert results["ec2_instances_processed"] == 1
        assert results["ebs_volumes_processed"] == 1
        assert results["cost_records_processed"] == 1
        assert len(results["errors"]) == 0
        
        assert mock_upsert.call_count == 2
        mock_upsert.assert_any_call(
            resource_id="i-test1",
            resource_type="ec2_instance",
            region="ap-south-1",
            status="running"
        )
        mock_upsert.assert_any_call(
            resource_id="vol-test1",
            resource_type="ebs_volume",
            region="ap-south-1",
            status="in-use"
        )

    @patch('app.services.aws_ingestion.sync_aws_costs')
    @patch('app.services.aws_ingestion.discover_ec2_instances')
    @patch('app.services.aws_ingestion.discover_ebs_volumes')
    def test_sync_aws_resources_api_error(self, mock_discover_ebs, mock_discover_ec2, mock_sync_costs):
        """Test synchronization when an AWS API error occurs."""
        mock_discover_ec2.side_effect = AWSApiError("AWS is down")
        mock_discover_ebs.return_value = []
        mock_sync_costs.return_value = []
        
        results = sync_aws_resources()
        
        assert results["ec2_instances_processed"] == 0
        assert results["ebs_volumes_processed"] == 0
        assert len(results["errors"]) == 1
        assert "AWS is down" in results["errors"][0]

    @patch('app.services.aws_ingestion.sync_aws_costs')
    @patch('app.services.aws_ingestion.discover_ec2_instances')
    @patch('app.services.aws_ingestion.discover_ebs_volumes')
    @patch('app.services.aws_ingestion.ResourceRepository.upsert_resource')
    def test_sync_idempotency_via_upsert(self, mock_upsert, mock_discover_ebs, mock_discover_ec2, mock_sync_costs):
        """Test that multiple syncs just call upsert safely."""
        mock_discover_ec2.return_value = [MOCK_EC2_DATA]
        mock_discover_ebs.return_value = []
        mock_sync_costs.return_value = []
        
        sync_aws_resources()
        sync_aws_resources()
        
        assert mock_upsert.call_count == 2

    @patch('app.services.aws_ingestion.sync_aws_costs')
    @patch('app.services.aws_ingestion.discover_ec2_instances')
    @patch('app.services.aws_ingestion.discover_ebs_volumes')
    @patch('app.services.aws_ingestion.CloudWatchService')
    @patch('app.services.aws_ingestion.ResourceRepository.upsert_resource')
    @patch('app.services.aws_ingestion.ResourceRepository.upsert_metric')
    def test_sync_aws_resources_cloudwatch_integration(self, mock_upsert_metric, mock_upsert_resource, mock_cw_service_class, mock_discover_ebs, mock_discover_ec2, mock_sync_costs):
        """Test that CloudWatch metrics are properly fetched and persisted during ingestion."""
        mock_discover_ec2.return_value = [MOCK_EC2_DATA]
        mock_discover_ebs.return_value = []
        mock_sync_costs.return_value = []
        
        mock_db_resource = MagicMock()
        mock_db_resource.id = 99
        mock_upsert_resource.return_value = mock_db_resource
        
        mock_cw_instance = MagicMock()
        mock_cw_instance.get_ec2_cpu_utilization.return_value = {
            "resource_id": "i-test1",
            "metric_name": "CPUUtilization",
            "average_cpu": 8.60,
            "datapoint_count": 1
        }
        mock_cw_service_class.return_value = mock_cw_instance
        
        sync_aws_resources()
        
        mock_cw_instance.get_ec2_cpu_utilization.assert_called_once_with("i-test1")
        mock_upsert_metric.assert_called_once_with(
            resource_db_id=99,
            metric_name="cpu_utilization",
            metric_value=8.60
        )
