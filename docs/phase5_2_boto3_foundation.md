# Phase 5.2 — Boto3 Foundation

## Purpose
Phase 5.2 establishes the integration foundation between the Cloud FinOps Optimizer and AWS. This phase securely introduces the Boto3 SDK into the application, implements a reliable pattern for connection pooling and service clients, and verifies connectivity, without modifying any real AWS resources or making discovery calls.

## Architecture
The AWS integration is managed by the new `AWSClientFactory` module located at `app/services/aws_client.py`.

This module abstracts the raw Boto3 logic away from the core application, providing:
- A standardized `get_client(service_name)` interface.
- Automatic region configuration through `config.py`.
- Custom, readable application-level exceptions (`AWSCredentialsError`, `AWSConnectionError`, `AWSApiError`) mapped cleanly from low-level `botocore` errors.

## Configuration & Credential Strategy
**Security First:** The application **never** stores hardcoded AWS credentials in source code or `config.py`.

Instead, the `AWSClientFactory` relies exclusively on the standard AWS credential resolution chain:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`).
2. Shared credential files (`~/.aws/credentials`).
3. IAM Roles (for future EC2/ECS/EKS deployment).

The `.env.example` file explicitly omits secret keys to avoid accidental credential commits. The only required environment configuration is `AWS_DEFAULT_REGION` (defaulting to `ap-south-1`).

## Connectivity Verification
A new safe `verify_connectivity()` method relies on the `STS` service (Security Token Service). By calling `sts.get_caller_identity()`, the application verifies network egress, validates the authentication chain, and confirms the active Account ID and IAM ARN — all strictly read-only operations that are guaranteed not to incur charges or modify resources.

## Testing Strategy
To prevent accidental AWS interactions or billing during CI/CD, the test suite (`tests/test_aws_client.py`) heavily utilizes `unittest.mock.patch`.
- `boto3.Session` is fully mocked.
- Exception handling branches (e.g. invalid credentials vs. network partition) are verified by manually injecting `botocore.exceptions`.
- Real AWS credentials are NOT required to pass the test suite.

## What is Intentionally NOT Implemented Yet
- **Resource Discovery**: No EC2, EBS, or S3 resources are queried yet. The application still uses the mock datasets established in Phases 1-4.
- **Resource Modification**: The application remains strictly read-only.
- **Cost Explorer Integration**: Scheduled for a later phase.

## Next Phase
**Phase 5.3 (AWS Resource Discovery)** will introduce active read-only calls to fetch live EC2 instances, EBS volumes, and S3 bucket configurations, seamlessly integrating them into the existing FinOps analysis pipeline established in Phase 4.
