# Phase 5.6 — AWS Cost Explorer / Cost Data Integration

## Overview & Purpose

Phase 5.6 integrates AWS Cost Explorer into the Cloud FinOps Optimizer platform. This enables retrieving real daily AWS unblended cost metrics via Boto3, normalizing financial data with `Decimal` precision, and idempotently persisting cost history into the local PostgreSQL database using the existing `CostRecord` model and repository pattern.

---

## Data Flow Architecture

```
AWS Cost Explorer (get_cost_and_usage)
              ↓
AWSCostService (app/services/aws_cost.py)
              ↓
Decimal Data Normalization
              ↓
ResourceRepository.upsert_cost_record (app/repositories/resource_repository.py)
              ↓
PostgreSQL Database (cost_records table)
```

---

## AWS API & Technical Details

### API Endpoint
- **Service**: Cost Explorer (`ce`)
- **API Call**: `get_cost_and_usage`
- **Granularity**: `DAILY`
- **Metrics**: `UnblendedCost`

### IAM Permissions Required
- `ce:GetCostAndUsage`

### Date-Range Behavior
- AWS Cost Explorer `End` date is exclusive.
- Default configuration queries the previous 7 days from UTC today (`start_date = today - 7 days`, `end_date = today`).
- The service supports custom date ranges passed as `'YYYY-MM-DD'` strings.
- Validates that `start_date < end_date`.

---

## Data Normalization & Data Model

### Normalized Data Structure
The `AWSCostService` extracts values from `ResultsByTime` into:
```python
{
    "start_date": "2026-09-23",
    "end_date": "2026-09-24",
    "amount": Decimal("0.0000000074"),
    "currency": "USD",
    "estimated": True
}
```

### Database Persistence (`CostRecord`)
- **Model**: Uses existing `CostRecord` model (`app/models.py`).
- **Resource Linking**: Stores account-level cost data under a parent `AWS_ACCOUNT` resource record (`resource_id="AWS_ACCOUNT"`, `resource_type="AWS_ACCOUNT"`, `region="global"`).
- **Idempotency**: `ResourceRepository.upsert_cost_record(resource_db_id, monthly_cost, recorded_at)` checks if a record for the specified resource and timestamp already exists. If found, it updates `monthly_cost`; otherwise, it inserts a new record. Repeated runs do not create duplicate entries.

---

## Error Handling

- **`AWSCredentialsError`**: Raised on missing AWS credentials, invalid auth tokens (`AuthFailure`, `AccessDeniedException`).
- **`AWSConnectionError`**: Raised when network or endpoint connection fails (`EndpointConnectionError`).
- **`AWSApiError`**: Raised on general boto3 AWS API exceptions or malformed cost data values.
- **Graceful Failure**: `sync_aws_resources()` catches cost synchronization errors to ensure resource ingestion (EC2/EBS) succeeds even if Cost Explorer access fails or has missing data.

---

## Verification & Testing

### Unit Tests
Run full pytest suite:
```bash
pytest
```
- Total tests passing: 120 / 120.
- `tests/test_aws_cost.py` covers client creation, daily cost parsing, Decimal handling, empty responses, missing fields, ClientError, invalid date ranges, database persistence, and idempotency.

### Manual Verification Script
Run the verification script:
```bash
python scripts/verify_costs.py
```
Outputs:
- Daily cost breakdown for the last 7 days.
- Total cost and period count.
- AWS error report.
- PostgreSQL database persistence confirmation.
