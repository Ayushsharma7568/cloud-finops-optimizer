# Phase 5.4 — AWS Database Integration

## Purpose
Phase 5.4 establishes the bridge between the real-time AWS Boto3 discovery logic built in Phase 5.3 and the PostgreSQL persistence layer introduced in Phase 4. It provides a reliable, idempotent ingestion service to synchronize discovered EC2 instances and EBS volumes into the `resources` table.

## Architecture
The integration is managed by a new service layer module: `app/services/aws_ingestion.py`.

### Flow:
1. `sync_aws_resources()` coordinates the AWS discovery layer.
2. It invokes `discover_ec2_instances()` and `discover_ebs_volumes()`.
3. The normalized dictionaries are mapped directly to `ResourceRepository.upsert_resource()`.
4. The database idempotently handles record creation versus status/region updates.

This architecture intentionally preserves the strict separation of concerns established in Phase 4; raw SQLAlchemy objects or queries never leak into the Boto3 discovery layer, and Boto3 logic never leaks into the repository layer.

## Idempotency and Duplication Prevention
By utilizing `upsert_resource(resource_id, resource_type, region, status)`, the ingestion service guarantees that:
- If a cloud resource ID (e.g. `i-12345678`) does not exist, a new record is safely created.
- If the resource ID already exists, its mutable attributes (like its running `status`) are safely updated.
- Repeated executions of `sync_aws_resources()` will never create duplicate database entries.

## Security & Scoping
- The sync process is strictly **read-only** relative to AWS.
- It relies entirely on the configuration and client factory built in Phase 5.2.
- The sync process is currently decoupled from the main Flask orchestrator / web UI to prevent blocking operations or unexpected AWS charges on simple page reloads.

## Testing Strategy
The integration is fully tested using `unittest.mock`.
- `tests/test_aws_ingestion.py` intercepts the Boto3 discovery outputs and verifies they are mapped correctly into the `ResourceRepository` upsert calls.
- Both successful upserts and API failures (like `AWSApiError`) are covered without requiring real database hits or network calls.

## Local Verification
Developers can manually trigger the synchronization pipeline safely from the CLI using:
```bash
python scripts/sync_aws_to_db.py
```
This script initializes the Flask context, synchronizes AWS with the local PostgreSQL database, and outputs a summary of instances and volumes processed.

## Next Phase
In future phases, the data ingestion pipeline can be triggered on a schedule (e.g. via Celery/Cron), and the UI will be updated to display the live AWS data instead of the Phase 1 mock seed data.
