# Phase 5.5 — AWS CloudWatch Metrics Integration

## Purpose
Phase 5.5 integrates Amazon CloudWatch to fetch real CPU metrics for EC2 instances. This replaces placeholder/hardcoded metric values, bringing the system closer to a production-ready FinOps tool.

## Implementation Details

### Service (`app/services/aws_cloudwatch.py`)
A dedicated `CloudWatchService` utilizes `boto3` (`GetMetricStatistics`) to fetch the `CPUUtilization` metric from the `AWS/EC2` namespace.

**Metric Constraints:**
- **Namespace:** `AWS/EC2`
- **Metric Name:** `CPUUtilization`
- **Dimensions:** `InstanceId`
- **Statistic:** `Average`
- **Period:** Configurable (default 86400 seconds / 1 day)
- **Lookback Window:** Configurable (default 14 days)

### Missing Data Handling
A missing CloudWatch datapoint is explicitly NOT treated as 0% CPU utilization. This is crucial because a stopped instance generates no datapoints, but substituting 0% would incorrectly imply the instance is running and entirely idle (which influences waste detection logic differently). 
If the API returns an empty `Datapoints` array, the service returns `average_cpu: None` and `datapoint_count: 0`.

### Database Integration
The existing `ResourceMetric` model in PostgreSQL was retained. To prevent duplicate metric records during repeated ingestions, `ResourceRepository.upsert_metric()` was added. This safely updates the latest known `metric_value` (or inserts it if it doesn't exist) matching the `resource_id` and `metric_name`.

### Architecture & Error Handling
- Leverages the existing `AWSClientFactory` and custom exception hierarchy (`AWSApiError`, `AWSConnectionError`) from Phase 5.2.
- Keeps AWS-specific structures contained within the service. Responses are normalized to standard Python dictionaries before returning.

## Testing
Unit tests are fully implemented (`tests/test_aws_cloudwatch.py`) using mocked Boto3 responses, covering successful metric retrieval, empty data responses, and expected AWS API errors. Real AWS credentials are not required for tests.

A manual verification script `scripts/verify_cloudwatch.py` allows testing the logic safely against a real account without modifying any infrastructure.
