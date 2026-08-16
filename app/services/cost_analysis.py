"""Service for analyzing cloud resource costs, utilization, and waste."""

from collections import Counter

from config import AnalysisThresholds


# ---------------------------------------------------------------------------
# Resource metrics
# ---------------------------------------------------------------------------

def count_resources_by_type(data: dict) -> dict[str, int]:
    """Count total resources per service type."""
    return {service: len(resources) for service, resources in data.items()}


def count_resources_by_region(data: dict) -> dict[str, int]:
    """Count total resources across all services grouped by region."""
    regions: Counter = Counter()
    for resources in data.values():
        for r in resources:
            regions[r.get("region", "unknown")] += 1
    return dict(regions)


def count_ec2_by_status(ec2_data: list[dict]) -> dict[str, int]:
    """Count EC2 instances by status (running, stopped, etc.)."""
    statuses: Counter = Counter()
    for instance in ec2_data:
        statuses[instance.get("status", "unknown")] += 1
    return dict(statuses)


# ---------------------------------------------------------------------------
# Cost metrics
# ---------------------------------------------------------------------------

def _total_cost(resources: list[dict]) -> float:
    """Sum monthly_cost across a list of resources."""
    return sum(r.get("monthly_cost", 0.0) for r in resources)


def calculate_cost_breakdown(data: dict) -> dict:
    """Calculate per-service and total monthly costs.

    Returns:
        Dict with keys: total, ec2, ebs, s3 (all floats).
    """
    ec2_cost = _total_cost(data.get("ec2", []))
    ebs_cost = _total_cost(data.get("ebs", []))
    s3_cost = _total_cost(data.get("s3", []))
    return {
        "total": round(ec2_cost + ebs_cost + s3_cost, 2),
        "ec2": round(ec2_cost, 2),
        "ebs": round(ebs_cost, 2),
        "s3": round(s3_cost, 2),
    }


# ---------------------------------------------------------------------------
# Utilization metrics
# ---------------------------------------------------------------------------

def calculate_ec2_utilization(ec2_data: list[dict]) -> dict:
    """Calculate average CPU and memory utilization for running EC2 instances.

    Returns:
        Dict with avg_cpu and avg_memory (floats), or 0.0 if no running instances.
    """
    running = [i for i in ec2_data if i.get("status") == "running"]
    if not running:
        return {"avg_cpu": 0.0, "avg_memory": 0.0}

    avg_cpu = sum(i.get("cpu_utilization", 0.0) for i in running) / len(running)
    avg_memory = sum(i.get("memory_utilization", 0.0) for i in running) / len(running)
    return {
        "avg_cpu": round(avg_cpu, 1),
        "avg_memory": round(avg_memory, 1),
    }


def calculate_ebs_utilization(ebs_data: list[dict]) -> dict:
    """Calculate total allocated vs. used EBS storage.

    Returns:
        Dict with total_allocated_gb, total_used_gb, and utilization_pct.
    """
    total_allocated = sum(v.get("size_gb", 0.0) for v in ebs_data)
    total_used = sum(v.get("used_gb", 0.0) for v in ebs_data)
    utilization_pct = (total_used / total_allocated * 100) if total_allocated > 0 else 0.0
    return {
        "total_allocated_gb": round(total_allocated, 1),
        "total_used_gb": round(total_used, 1),
        "utilization_pct": round(utilization_pct, 1),
    }


# ---------------------------------------------------------------------------
# Waste / underutilization detection
# ---------------------------------------------------------------------------

def detect_underutilized_resources(data: dict) -> list[dict]:
    """Identify resources that are underutilized or potentially wasteful.

    Uses thresholds from config.AnalysisThresholds.

    Returns:
        List of dicts, each with: resource_id, resource_type, reason,
        and relevant metric values.
    """
    flags: list[dict] = []

    # EC2 checks
    for instance in data.get("ec2", []):
        resource_id = instance.get("resource_id", "unknown")

        # Stopped instances still incur EBS costs and occupy reservations
        if instance.get("status") == "stopped":
            flags.append({
                "resource_id": resource_id,
                "resource_type": "EC2",
                "reason": "Instance is stopped",
                "monthly_cost": instance.get("monthly_cost", 0.0),
            })
            continue

        cpu = instance.get("cpu_utilization", 0.0)
        memory = instance.get("memory_utilization", 0.0)

        if cpu < AnalysisThresholds.EC2_CPU_UNDERUTILIZED:
            flags.append({
                "resource_id": resource_id,
                "resource_type": "EC2",
                "reason": f"Low CPU utilization ({cpu}%)",
                "monthly_cost": instance.get("monthly_cost", 0.0),
            })
        elif memory < AnalysisThresholds.EC2_MEMORY_UNDERUTILIZED:
            flags.append({
                "resource_id": resource_id,
                "resource_type": "EC2",
                "reason": f"Low memory utilization ({memory}%)",
                "monthly_cost": instance.get("monthly_cost", 0.0),
            })

    # EBS checks
    for volume in data.get("ebs", []):
        volume_id = volume.get("volume_id", "unknown")
        size_gb = volume.get("size_gb", 0.0)
        used_gb = volume.get("used_gb", 0.0)

        if volume.get("status") == "available":
            flags.append({
                "resource_id": volume_id,
                "resource_type": "EBS",
                "reason": "Volume is unattached",
                "monthly_cost": volume.get("monthly_cost", 0.0),
            })
            continue

        utilization = (used_gb / size_gb) if size_gb > 0 else 0.0
        if utilization < AnalysisThresholds.EBS_UTILIZATION_UNDERUTILIZED:
            flags.append({
                "resource_id": volume_id,
                "resource_type": "EBS",
                "reason": (
                    f"Low storage utilization "
                    f"({used_gb}/{size_gb} GB = {utilization:.0%})"
                ),
                "monthly_cost": volume.get("monthly_cost", 0.0),
            })

    return flags


# ---------------------------------------------------------------------------
# Aggregate summary
# ---------------------------------------------------------------------------

def generate_summary(data: dict) -> dict:
    """Produce a complete Phase 1 analysis summary.

    Args:
        data: Dict with 'ec2', 'ebs', 's3' resource lists (from data_loader).

    Returns:
        Dict containing all metrics needed by the dashboard.
    """
    cost_breakdown = calculate_cost_breakdown(data)
    ec2_util = calculate_ec2_utilization(data.get("ec2", []))
    ebs_util = calculate_ebs_utilization(data.get("ebs", []))
    underutilized = detect_underutilized_resources(data)

    return {
        "resource_counts": count_resources_by_type(data),
        "resources_by_region": count_resources_by_region(data),
        "ec2_status": count_ec2_by_status(data.get("ec2", [])),
        "costs": cost_breakdown,
        "ec2_utilization": ec2_util,
        "ebs_utilization": ebs_util,
        "underutilized_resources": underutilized,
        "total_resources": sum(len(v) for v in data.values()),
    }
