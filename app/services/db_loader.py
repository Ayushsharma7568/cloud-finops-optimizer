"""Data loader / correlation layer — transforms PostgreSQL database objects

into unified FinOps engine data structures.

Explicitly maintains the architectural boundary between:
1. Resource-level utilization/metadata
2. Account-level AWS Cost Explorer cost history
"""

from app.repositories.resource_repository import ResourceRepository


def load_data_from_db() -> dict:
    """Load resources, metrics, and cost history from PostgreSQL.

    Returns:
        dict: Standardized FinOps context dictionary containing:
            - 'ec2': list of EC2 resource dicts with metrics
            - 'ebs': list of EBS volume dicts with metrics
            - 's3': list of S3 bucket dicts with metrics
            - 'account_cost': float total of account-level costs
            - 'account_cost_records': list of daily account-level cost records
            - 'summary_metrics': counts of resource/metric availability
    """
    resources = ResourceRepository.get_all_resources()

    data = {
        "ec2": [],
        "ebs": [],
        "s3": [],
        "account_cost": 0.0,
        "account_cost_records": [],
        "summary_metrics": {
            "total_resources": 0,
            "ec2_total": 0,
            "ec2_running": 0,
            "ec2_stopped": 0,
            "ec2_with_cpu_data": 0,
            "ec2_without_cpu_data": 0,
            "ebs_total": 0,
            "account_cost_periods": 0,
        },
    }

    account_cost_sum = 0.0

    for res in resources:
        res_type_lower = res.resource_type.lower()

        # Handle Account-Level Cost Record resource separately
        if res.resource_id == "AWS_ACCOUNT" or res.resource_type == "AWS_ACCOUNT":
            for cost in res.cost_records:
                account_cost_sum += cost.monthly_cost
                data["account_cost_records"].append({
                    "monthly_cost": cost.monthly_cost,
                    "recorded_at": cost.recorded_at
                })
            data["account_cost"] = round(account_cost_sum, 10)
            data["summary_metrics"]["account_cost_periods"] = len(res.cost_records)
            continue

        # Reconstruct base resource representation
        item = {
            "resource_id": res.resource_id,
            "region": res.region,
            "status": res.status,
            "state": res.status,  # backward compatibility
            "instance_id": res.resource_id,
            "volume_id": res.resource_id,
            "bucket_name": res.resource_id,
            "instance_type": "unknown",
            "volume_type": "unknown",
            "cpu_utilization": None,
            "memory_utilization": None,
        }

        # Resource-level cost (ONLY if directly attached to this specific resource)
        if res.cost_records:
            item["monthly_cost"] = res.cost_records[-1].monthly_cost
        else:
            item["monthly_cost"] = 0.0

        # Metrics mapping
        for metric in res.metrics:
            item[metric.metric_name] = metric.metric_value
            if metric.metric_name == "cpu_utilization":
                item["cpu_utilization"] = metric.metric_value
                item["cpu_utilization_percent"] = metric.metric_value
            elif metric.metric_name == "memory_utilization":
                item["memory_utilization"] = metric.metric_value
                item["memory_utilization_percent"] = metric.metric_value
            elif metric.metric_name == "storage_utilization":
                item["storage_utilization"] = metric.metric_value
            elif metric.metric_name == "total_size_gb":
                item["size_gb"] = metric.metric_value

        # EBS defaults computation
        if res_type_lower == "ebs" or res_type_lower == "ebs_volume":
            if "size_gb" not in item:
                item["size_gb"] = 100.0
            if "storage_utilization" in item:
                item["used_gb"] = item["size_gb"] * (item["storage_utilization"] / 100.0)
            else:
                item["used_gb"] = 0.0

        # Group resources into service lists
        if res_type_lower in ["ec2", "ec2_instance"]:
            data["ec2"].append(item)
            data["summary_metrics"]["ec2_total"] += 1
            if res.status == "running":
                data["summary_metrics"]["ec2_running"] += 1
            elif res.status == "stopped":
                data["summary_metrics"]["ec2_stopped"] += 1

            if item["cpu_utilization"] is not None:
                data["summary_metrics"]["ec2_with_cpu_data"] += 1
            else:
                data["summary_metrics"]["ec2_without_cpu_data"] += 1

        elif res_type_lower in ["ebs", "ebs_volume"]:
            data["ebs"].append(item)
            data["summary_metrics"]["ebs_total"] += 1

        elif res_type_lower in ["s3", "s3_bucket"]:
            data["s3"].append(item)

    data["summary_metrics"]["total_resources"] = (
        len(data["ec2"]) + len(data["ebs"]) + len(data["s3"])
    )

    return data


def load_finops_correlation_summary() -> dict:
    """Helper method providing detailed correlation analysis for verification."""
    data = load_data_from_db()

    ec2_resources = data["ec2"]
    account_cost_preserved = "AWS_ACCOUNT" not in [r["resource_id"] for r in ec2_resources]
    
    # Verify no EC2 resource inherited the total account cost
    fake_resource_costs = any(
        r["monthly_cost"] == data["account_cost"] and data["account_cost"] > 0
        for r in ec2_resources
    )

    return {
        "data": data,
        "account_cost_preserved_separately": account_cost_preserved,
        "fake_resource_costs_detected": fake_resource_costs,
    }
