"""Tests for the AWS Client Factory."""

import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import NoCredentialsError, ClientError, EndpointConnectionError
from app.services.aws_client import (
    AWSClientFactory,
    AWSCredentialsError,
    AWSConnectionError,
    AWSApiError
)


class TestAWSClientFactory:
    
    @patch('app.services.aws_client.boto3.Session')
    def test_factory_initialization(self, mock_session):
        """Test that the factory initializes a session with the configured region."""
        factory = AWSClientFactory()
        mock_session.assert_called_once_with(region_name=factory.region)
        assert factory.session == mock_session.return_value

    @patch('app.services.aws_client.boto3.Session')
    def test_get_client(self, mock_session):
        """Test that get_client calls the session's client method."""
        factory = AWSClientFactory()
        mock_client = MagicMock()
        factory.session.client.return_value = mock_client
        
        client = factory.get_client('ec2')
        factory.session.client.assert_called_once_with('ec2')
        assert client == mock_client

    @patch('app.services.aws_client.boto3.Session')
    def test_verify_connectivity_success(self, mock_session):
        """Test successful connectivity verification."""
        factory = AWSClientFactory()
        
        # Mock STS client and its response
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/test-user",
            "UserId": "AIDACKCEVSQ6C2EXAMPLE"
        }
        
        factory.session.client.return_value = mock_sts
        
        result = factory.verify_connectivity()
        
        assert result["Account"] == "123456789012"
        assert result["Arn"] == "arn:aws:iam::123456789012:user/test-user"
        assert result["UserId"] == "AIDACKCEVSQ6C2EXAMPLE"
        assert result["Region"] == factory.region


class TestAWSErrorHandling:

    @patch('app.services.aws_client.boto3.Session')
    def test_no_credentials_error(self, mock_session):
        """Test handling of missing credentials."""
        factory = AWSClientFactory()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = NoCredentialsError()
        factory.session.client.return_value = mock_sts
        
        with pytest.raises(AWSCredentialsError, match="No AWS credentials found"):
            factory.verify_connectivity()

    @patch('app.services.aws_client.boto3.Session')
    def test_endpoint_connection_error(self, mock_session):
        """Test handling of network connectivity issues."""
        factory = AWSClientFactory()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = EndpointConnectionError(endpoint_url="https://sts.amazonaws.com")
        factory.session.client.return_value = mock_sts
        
        with pytest.raises(AWSConnectionError, match="Could not connect to AWS endpoints"):
            factory.verify_connectivity()

    @patch('app.services.aws_client.boto3.Session')
    def test_client_error_auth_failure(self, mock_session):
        """Test handling of invalid credentials (AuthFailure)."""
        factory = AWSClientFactory()
        mock_sts = MagicMock()
        
        # Create a mock ClientError
        error_response = {'Error': {'Code': 'AuthFailure', 'Message': 'Auth failure'}}
        mock_sts.get_caller_identity.side_effect = ClientError(error_response, 'GetCallerIdentity')
        factory.session.client.return_value = mock_sts
        
        with pytest.raises(AWSCredentialsError, match="AWS credentials rejected"):
            factory.verify_connectivity()

    @patch('app.services.aws_client.boto3.Session')
    def test_client_error_other(self, mock_session):
        """Test handling of non-auth related ClientErrors."""
        factory = AWSClientFactory()
        mock_sts = MagicMock()
        
        # Create a mock ClientError
        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Internal server error'}}
        mock_sts.get_caller_identity.side_effect = ClientError(error_response, 'GetCallerIdentity')
        factory.session.client.return_value = mock_sts
        
        with pytest.raises(AWSApiError, match="AWS API Error"):
            factory.verify_connectivity()
