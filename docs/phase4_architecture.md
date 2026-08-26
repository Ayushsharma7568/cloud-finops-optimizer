# Phase 4 — Database & Persistent FinOps Data

## Architecture Overview
Phase 4 introduces PostgreSQL as the persistent data layer to replace the purely in-memory structures from previous phases, while retaining backwards compatibility for tests and services. 

```
PostgreSQL
     ↓
SQLAlchemy (app/models.py)
     ↓
Repository / Data Access (app/repositories/)
     ↓
Data Object Mapping (app/services/db_loader.py)
     ↓
FinOps Services (Core Logic)
     ↓
Persistence of Findings & Recommendations
     ↓
Flask Dashboard (app/routes.py)
```

## Database Schema
The database uses 6 primary tables:
1. **resources**: Contains core resource metadata (`id`, `resource_id`, `resource_type`, `region`, `status`).
2. **resource_metrics**: Contains utilization data (e.g. `cpu_utilization`, `memory_utilization`).
3. **cost_records**: Contains monthly historical costs.
4. **analysis_runs**: Tracks FinOps engine executions (`started_at`, `status`, `completed_at`, `potential_monthly_savings`).
5. **optimization_findings**: Waste detection findings (`issue_type`, `severity`).
6. **recommendations**: Final action suggestions (`action_category`, `recommendation_text`, `confidence`).

## Data Import
The mock data (CSV) is maintained as seed data. The script `scripts/seed_data.py` translates the CSV files into PostgreSQL structures, utilizing the Repository layer.

## Repositories
We implemented the Repository Pattern (`ResourceRepository`, `AnalysisRepository`) to abstract SQLAlchemy interactions from the business logic.

## Why AWS API (Boto3) is excluded
In this phase, we only implemented local PostgreSQL persistence. Real Boto3 integration involves real credentials, network boundaries, rate limits, and actual cloud state. By abstracting the Data Layer first, future Phase 5 can simply replace the DB loader with a Boto3 loader, without needing to touch the internal FinOps waste detector engine.
