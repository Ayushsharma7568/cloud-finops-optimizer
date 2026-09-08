"""AWS Client Factory and Connection Utilities.

Provides a clean abstraction over boto3 for creating sessions and clients
using the standard AWS credential chain. Does not store real credentials.
"""

import logging
import boto3
from botocore.exceptions import NoCredentialsError, ClientError, EndpointConnectionError
from config import Config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AWSCredentialsError(Exception):
    """Raised when AWS credentials are not found or invalid."""
    pass


class AWSConnectionError(Exception):
    """Raised when the application cannot connect to AWS endpoints."""
    pass


class AWSApiError(Exception):
    """Raised when an AWS API call fails."""
    pass


# ---------------------------------------------------------------------------
# Client Factory
# ---------------------------------------------------------------------------

class AWSClientFactory:
    """Factory for creating and managing AWS Boto3 clients."""

    def __init__(self):
        self.region = Config.AWS_DEFAULT_REGION
        # Create a base session. boto3 will automatically search for credentials
        # in env vars, shared credential file (~/.aws/credentials), IAM roles, etc.
        try:
            self.session = boto3.Session(region_name=self.region)
        except Exception as e:
            logger.error("Failed to initialize AWS Session: %s", e)
            raise AWSConnectionError(f"Failed to initialize AWS Session: {e}")

    def get_client(self, service_name: str):
        """Create and return a boto3 client for the specified service.
        
        Supported services initially: ec2, s3, cloudwatch, ce
        """
        try:
            return self.session.client(service_name)
        except Exception as e:
            logger.error("Failed to create client for %s: %s", service_name, e)
            raise AWSConnectionError(f"Failed to create client for {service_name}: {e}")

    def verify_connectivity(self) -> dict:
        """Verify AWS connectivity and identity.
        
        Calls STS GetCallerIdentity to verify that credentials are valid
        and the application can communicate with AWS.
        
        Returns:
            dict containing Account, Arn, and UserId if successful.
            
        Raises:
            AWSCredentialsError: If credentials are missing or invalid.
            AWSConnectionError: If network connectivity fails.
            AWSApiError: For other AWS API errors.
        """
        try:
            sts_client = self.get_client('sts')
            identity = sts_client.get_caller_identity()
            
            return {
                "Account": identity.get("Account"),
                "Arn": identity.get("Arn"),
                "UserId": identity.get("UserId"),
                "Region": self.region
            }
            
        except NoCredentialsError:
            raise AWSCredentialsError("No AWS credentials found. Please configure the environment or AWS CLI.")
        except EndpointConnectionError as e:
            raise AWSConnectionError(f"Could not connect to AWS endpoints: {e}")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code in ['InvalidClientTokenId', 'AccessDenied', 'SignatureDoesNotMatch', 'AuthFailure']:
                raise AWSCredentialsError(f"AWS credentials rejected ({error_code}).")
            raise AWSApiError(f"AWS API Error: {e}")
        except Exception as e:
            raise AWSApiError(f"Unexpected error during AWS connectivity check: {e}")
