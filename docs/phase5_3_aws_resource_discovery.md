# Phase 5.3 — AWS Resource Discovery: EC2 + EBS

## Purpose
Phase 5.3 introduces live resource discovery capabilities using the Boto3 foundation established in Phase 5.2. This phase implements isolated service modules for fetching and normalizing real AWS EC2 instances and EBS volumes. 

## Architecture
Two new discovery modules have been introduced:
- `app/services/aws_ec2_discovery.py`
- `app/services/aws_ebs_discovery.py`

Both modules rely on `AWSClientFactory` to obtain a session and Boto3 `ec2` client.

## Discovery Mechanics

### Pagination
AWS APIs return paginated results for large resource counts. The discovery services use `boto3` paginators (`get_paginator('describe_instances')` and `get_paginator('describe_volumes')`) to safely iterate over all pages, guaranteeing that no resources are missed regardless of the account size.

### Normalization
The raw Boto3 dictionary structures are complex and deeply nested. The discovery services normalize this data into a flat, predictable structure tailored for the FinOps engine.

Example normalized output:
```json
{
    "resource_id": "i-1234567890abcdef0",
    "resource_type": "ec2_instance",
    "region": "ap-south-1",
    "state": "running",
    "metadata": {
        "instance_type": "t3.micro",
        "name": "web-server-1",
        "public_ip": "203.0.113.5",
        "tags": {"Environment": "production"}
    }
}
```

Optional fields (such as `PublicIpAddress` for EC2, or `Attachments` for EBS) are handled safely using `.get()` to prevent KeyErrors.

### Region Handling
The region configuration (`AWS_DEFAULT_REGION`) defaults to `ap-south-1` as established in Phase 5.2. The discovery services inherit this region cleanly from the client factory.

### Error Handling
The discovery functions inherit the custom exceptions (`AWSCredentialsError`, `AWSConnectionError`, `AWSApiError`) mapped from `botocore.exceptions`. If an error occurs, it bubbles up safely without exposing secrets.

## Security & Read-Only Guarantees
- The implementation uses only read-only `DescribeInstances` and `DescribeVolumes` API calls.
- No modifying operations (`RunInstances`, `DeleteVolume`, etc.) have been introduced.
- Credentials remain managed exclusively through the AWS credential chain (environment variables or `~/.aws/credentials`).

## Testing Strategy
The test suite utilizes `unittest.mock` to intercept Boto3 clients and paginators.
- EC2 and EBS discovery logic is fully tested against simulated AWS responses.
- Tests cover paginated results, missing optional fields (like no public IP or unattached volumes), empty result sets, and API failure scenarios.
- Real AWS API calls are entirely prevented during unit tests.

## What is NOT Implemented
- S3 bucket discovery, CloudWatch metrics, and Cost Explorer integrations are deferred.
- The discovered EC2 and EBS resources **are not yet saved to the PostgreSQL database**.
- The existing FinOps engine and dashboard still run against the Phase 4 mock data.

## Local Verification
You can manually verify discovery against your local AWS account safely using:
```bash
python scripts/verify_aws_discovery.py
```
This script runs the discovery functions and prints the normalized output without interacting with the database.

## Next Phase
Phase 5.4 will integrate these normalized resources into the PostgreSQL persistence layer, allowing the FinOps engine to analyze real AWS data instead of the mock CSV seeds.
