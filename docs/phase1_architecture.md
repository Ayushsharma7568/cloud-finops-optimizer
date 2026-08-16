# Phase 1 — Mock Data Architecture

## Overview

Phase 1 uses CSV files to simulate cloud resource data. This allows the application to be developed and tested without requiring a real AWS account or API credentials.

## Supported Resource Types

### EC2 Instances (`data/ec2_resources.csv`)

| Field | Type | Description |
|-------|------|-------------|
| resource_id | string | Unique instance identifier (e.g., `i-0a1b2c3d4e5f00001`) |
| instance_type | string | AWS instance type (e.g., `t3.micro`, `m5.large`) |
| region | string | AWS region (e.g., `us-east-1`) |
| status | string | `running` or `stopped` |
| cpu_utilization | float | Average CPU utilization percentage (0–100) |
| memory_utilization | float | Average memory utilization percentage (0–100) |
| monthly_cost | float | Estimated monthly cost in USD |

### EBS Volumes (`data/ebs_volumes.csv`)

| Field | Type | Description |
|-------|------|-------------|
| volume_id | string | Unique volume identifier |
| volume_type | string | Volume type (`gp2`, `gp3`, `io1`, `st1`) |
| region | string | AWS region |
| size_gb | float | Provisioned size in GB |
| used_gb | float | Currently used storage in GB |
| monthly_cost | float | Estimated monthly cost in USD |
| status | string | `in-use` or `available` |

### S3 Buckets (`data/s3_buckets.csv`)

| Field | Type | Description |
|-------|------|-------------|
| bucket_name | string | Bucket name |
| region | string | AWS region |
| storage_gb | float | Total storage used in GB |
| monthly_cost | float | Estimated monthly cost in USD |

## Analysis Flow

```
1. data_loader.py loads CSV files and validates columns/types
2. cost_analysis.py computes:
   - Resource counts (by type, region, status)
   - Cost breakdown (total + per-service)
   - EC2 utilization averages (CPU, memory)
   - EBS storage utilization
   - Underutilized/wasteful resource flags
3. routes.py calls generate_summary() and passes results to the template
4. index.html renders all metrics
```

## Underutilization Detection

Thresholds are defined in `config.py` → `AnalysisThresholds`:

| Check | Threshold | Default |
|-------|-----------|---------|
| EC2 CPU underutilized | Below percentage | 15% |
| EC2 memory underutilized | Below percentage | 15% |
| EBS storage underutilized | used/size ratio below | 20% |
| EC2 stopped | Status is `stopped` | — |
| EBS unattached | Status is `available` | — |

## Limitations

- Data is static mock data, not live AWS data.
- No database storage — data is loaded from CSV on each request.
- No optimization recommendations — only waste detection flags.
- No historical tracking or trend analysis.
- Thresholds are global, not per-instance-type.

These limitations will be addressed in later phases.
