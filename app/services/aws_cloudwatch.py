import logging
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError, EndpointConnectionError
from app.services.aws_client import AWSClientFactory, AWSApiError, AWSConnectionError

logger = logging.getLogger(__name__)

class CloudWatchService:
    """Service for retrieving AWS CloudWatch metrics."""

    def __init__(self, client_factory=None):
        self.client_factory = client_factory or AWSClientFactory()
        try:
            self.client = self.client_factory.get_client('cloudwatch')
        except Exception as e:
            logger.error("Failed to initialize CloudWatch client: %s", e)
            raise

    def get_ec2_cpu_utilization(self, instance_id: str, days: int = 14, period: int = 86400) -> dict:
        """Retrieve Average CPU Utilization for an EC2 instance.

        Args:
            instance_id (str): The EC2 Instance ID.
            days (int): Lookback window in days.
            period (int): Granularity in seconds.

        Returns:
            dict: Normalized metric data.
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        try:
            response = self.client.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average']
            )

            datapoints = response.get('Datapoints', [])
            
            if not datapoints:
                return {
                    "resource_id": instance_id,
                    "metric_name": "CPUUtilization",
                    "average_cpu": None,
                    "datapoint_count": 0,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "unit": "Percent"
                }

            # Calculate overall average from the returned averages
            total_avg = sum(dp['Average'] for dp in datapoints)
            overall_avg = total_avg / len(datapoints)

            return {
                "resource_id": instance_id,
                "metric_name": "CPUUtilization",
                "average_cpu": overall_avg,
                "datapoint_count": len(datapoints),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "unit": datapoints[0].get('Unit', 'Percent')
            }

        except EndpointConnectionError as e:
            logger.error("Connection error to CloudWatch for %s: %s", instance_id, e)
            raise AWSConnectionError(f"CloudWatch connection error: {e}")
        except ClientError as e:
            logger.error("AWS API error retrieving metrics for %s: %s", instance_id, e)
            raise AWSApiError(f"CloudWatch API error: {e}")
        except Exception as e:
            logger.error("Unexpected error retrieving metrics for %s: %s", instance_id, e)
            raise AWSApiError(f"Unexpected CloudWatch error: {e}")
