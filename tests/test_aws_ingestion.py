"""Tests for the AWS Database Ingestion Service."""

import pytest
from unittest.mock import patch, MagicMock
from app.services.aws_ingestion import sync_aws_resources, _ingest_resource
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

    @patch('app.services.aws_ingestion.discover_ec2_instances')
    @patch('app.services.aws_ingestion.discover_ebs_volumes')
    @patch('app.services.aws_ingestion.ResourceRepository.upsert_resource')
    def test_sync_aws_resources_success(self, mock_upsert, mock_discover_ebs, mock_discover_ec2):
        """Test successful synchronization of EC2 and EBS resources."""
        # Setup mocks
        mock_discover_ec2.return_value = [MOCK_EC2_DATA]
        mock_discover_ebs.return_value = [MOCK_EBS_DATA]
        
        # Call sync
        results = sync_aws_resources()
        
        # Verify
        assert results["ec2_instances_processed"] == 1
        assert results["ebs_volumes_processed"] == 1
        assert len(results["errors"]) == 0
        
        # Check upsert was called for both resources with correct parameters
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

    @patch('app.services.aws_ingestion.discover_ec2_instances')
    @patch('app.services.aws_ingestion.discover_ebs_volumes')
    def test_sync_aws_resources_api_error(self, mock_discover_ebs, mock_discover_ec2):
        """Test synchronization when an AWS API error occurs."""
        mock_discover_ec2.side_effect = AWSApiError("AWS is down")
        mock_discover_ebs.return_value = []
        
        results = sync_aws_resources()
        
        # It should handle the error gracefully without crashing
        assert results["ec2_instances_processed"] == 0
        assert results["ebs_volumes_processed"] == 0
        assert len(results["errors"]) == 1
        assert "AWS is down" in results["errors"][0]

    @patch('app.services.aws_ingestion.discover_ec2_instances')
    @patch('app.services.aws_ingestion.discover_ebs_volumes')
    @patch('app.services.aws_ingestion.ResourceRepository.upsert_resource')
    def test_sync_idempotency_via_upsert(self, mock_upsert, mock_discover_ebs, mock_discover_ec2):
        """Test that multiple syncs just call upsert safely."""
        mock_discover_ec2.return_value = [MOCK_EC2_DATA]
        mock_discover_ebs.return_value = []
        
        # First sync
        sync_aws_resources()
        # Second sync
        sync_aws_resources()
        
        # upsert should have been called twice, delegating the logic of
        # update vs create to the database layer correctly.
        assert mock_upsert.call_count == 2

