# Phase 5.7 — AWS Resource/Cost Correlation & FinOps Data Unification

## Overview & Purpose

Phase 5.7 establishes a clean data correlation and unification layer between PostgreSQL database entities and the core FinOps engine (`waste_detector`, `cost_analysis`, `recommendation_engine`, `savings_calculator`).

It unifies:
1. **Discovered AWS Resources** (EC2, EBS, S3)
2. **CloudWatch Metrics** (EC2 Average CPU utilization)
3. **AWS Cost Explorer Data** (Daily Unblended Account Cost)

---

## Architectural Data Flow

```
PostgreSQL Database
  ├── resources (EC2, EBS, S3)
  ├── resource_metrics (CloudWatch CPU utilization)
  └── cost_records (AWS_ACCOUNT daily costs & resource costs)
                       ↓
Repository Layer (app/repositories/resource_repository.py)
                       ↓
FinOps Correlation Layer (app/services/db_loader.py)
                       ↓
FinOps Analysis & Engine (waste_detector, cost_analysis, recommendation_engine)
                       ↓
Web Dashboard / Database Persistence
```

---

## Data Layer Boundaries & Rules

### 1. Account-Level Cost vs Resource-Level Cost
- AWS Cost Explorer `get_cost_and_usage` provides account-level cost metrics.
- These account-level cost records are persisted under a dedicated parent resource: `resource_id="AWS_ACCOUNT"`.
- The correlation layer (`db_loader.py`) loads `account_cost` and `account_cost_records` separately.
- **Rule**: Account-level cost is **NEVER** distributed, divided, or attached to individual EC2/EBS resources unless resource-specific cost attribution is provided by AWS.

### 2. Missing Metric Data Handling
- **CPU = 0.0%**: Indicates an actual CloudWatch metric was retrieved and measured 0.0% CPU usage.
- **CPU = None**: Indicates no CloudWatch metric datapoint was available for that instance.
- **Rule**: Missing CPU metrics (`None`) do **NOT** trigger underutilization warnings (`< 10%`). Missing data is preserved as `None` without converting to zero.

---

## Unification Structure

`db_loader.load_data_from_db()` constructs a standardized FinOps dictionary:
```python
{
    "ec2": [
        {
            "resource_id": "i-00e59d865239b917b",
            "region": "ap-south-1",
            "status": "running",
            "cpu_utilization": 8.60,
            "monthly_cost": 0.0
        }
    ],
    "ebs": [...],
    "s3": [...],
    "account_cost": 0.0000000527,
    "account_cost_records": [...],
    "summary_metrics": {
        "total_resources": 35,
        "ec2_total": 18,
        "ec2_running": 13,
        "ec2_stopped": 5,
        "ec2_with_cpu_data": 14,
        "ec2_without_cpu_data": 4,
        "ebs_total": 10,
        "account_cost_periods": 7
    }
}
```

---

## Verification & Testing

### Unit Tests
Run full test suite:
```bash
pytest
```
- Total test count: **130 / 130 passing**.
- `tests/test_finops_correlation.py` tests 10 core correlation scenarios including metric loading, missing metric safety, account cost separation, backward compatibility with Phase 4 mock data, empty database behavior, and full pipeline analysis.

### Verification Script
Run the manual correlation verification script:
```bash
python scripts/verify_finops_data.py
```
Output confirms:
- Resource counts and CloudWatch metric availability counts.
- Separate preservation of `AWS Account Cost`.
- Absence of fake resource-level cost generation.
