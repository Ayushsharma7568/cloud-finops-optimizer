"""Waste detection engine — identifies optimization opportunities.

Consumes loaded resource data and produces standardized OptimizationFinding
objects describing what could be optimized, why, and estimated savings.
"""

from dataclasses import dataclass, field
from enum import Enum
from math import ceil

from config import AnalysisThresholds, MockPricing


# ---------------------------------------------------------------------------
# Issue types and severity
# ---------------------------------------------------------------------------

class IssueType(str, Enum):
    """Standardized issue types for optimization findings."""

    UNDERUTILIZED_EC2 = "UNDERUTILIZED_EC2"
    STOPPED_EC2 = "STOPPED_EC2"
    UNDERUTILIZED_EBS = "UNDERUTILIZED_EBS"
    UNATTACHED_EBS = "UNATTACHED_EBS"


class Severity(str, Enum):
    """Finding severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ---------------------------------------------------------------------------
# Finding data structure
# ---------------------------------------------------------------------------

@dataclass
class OptimizationFinding:
    """A single optimization opportunity."""

    resource_id: str
    resource_type: str
    issue_type: IssueType
    severity: Severity
    reason: str
    recommended_action: str
    current_monthly_cost: float
    estimated_optimized_monthly_cost: float | None = None
    estimated_monthly_savings: float = 0.0
    estimated_annual_savings: float = 0.0

    def to_dict(self) -> dict:
        """Convert to a plain dict for template rendering."""
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "reason": self.reason,
            "recommended_action": self.recommended_action,
            "current_monthly_cost": self.current_monthly_cost,
            "estimated_optimized_monthly_cost": self.estimated_optimized_monthly_cost,
            "estimated_monthly_savings": self.estimated_monthly_savings,
            "estimated_annual_savings": self.estimated_annual_savings,
        }


# ---------------------------------------------------------------------------
# Severity assignment
# ---------------------------------------------------------------------------

def _assign_severity(monthly_cost: float, monthly_savings: float) -> Severity:
    """Assign severity based on the potential monthly savings.

    HIGH:   savings >= HIGH_SEVERITY_COST
    MEDIUM: savings >= MEDIUM_SEVERITY_COST
    LOW:    savings < MEDIUM_SEVERITY_COST
    """
    if monthly_savings >= AnalysisThresholds.HIGH_SEVERITY_COST:
        return Severity.HIGH
    if monthly_savings >= AnalysisThresholds.MEDIUM_SEVERITY_COST:
        return Severity.MEDIUM
    return Severity.LOW


# ---------------------------------------------------------------------------
# EC2 detection
# ---------------------------------------------------------------------------

def _detect_ec2_findings(ec2_data: list[dict]) -> list[OptimizationFinding]:
    """Detect optimization opportunities in EC2 instances."""
    findings: list[OptimizationFinding] = []

    for instance in ec2_data:
        resource_id = instance.get("resource_id", "unknown")
        cost = instance.get("monthly_cost", 0.0)
        status = instance.get("status", "")

        # --- Stopped instances ---
        if status == "stopped":
            findings.append(OptimizationFinding(
                resource_id=resource_id,
                resource_type="EC2",
                issue_type=IssueType.STOPPED_EC2,
                severity=Severity.LOW,
                reason="Instance is stopped but may still incur associated costs "
                       "(e.g., attached EBS volumes, Elastic IPs).",
                recommended_action=(
                    "Review whether this instance is still required. "
                    "Consider terminating it if it is no longer needed."
                ),
                current_monthly_cost=cost,
                estimated_optimized_monthly_cost=0.0,
                estimated_monthly_savings=cost,
                estimated_annual_savings=round(cost * 12, 2),
            ))
            continue

        # --- Underutilized running instances ---
        cpu = instance.get("cpu_utilization", 0.0)
        memory = instance.get("memory_utilization", 0.0)

        is_cpu_low = cpu < AnalysisThresholds.EC2_CPU_UNDERUTILIZED
        is_mem_low = memory < AnalysisThresholds.EC2_MEMORY_UNDERUTILIZED

        if is_cpu_low or is_mem_low:
            optimized_cost = round(cost * MockPricing.EC2_DOWNSIZE_COST_RATIO, 2)
            monthly_savings = round(cost - optimized_cost, 2)

            if is_cpu_low and is_mem_low:
                metric_detail = f"CPU {cpu}%, Memory {memory}%"
            elif is_cpu_low:
                metric_detail = f"CPU {cpu}%"
            else:
                metric_detail = f"Memory {memory}%"

            findings.append(OptimizationFinding(
                resource_id=resource_id,
                resource_type="EC2",
                issue_type=IssueType.UNDERUTILIZED_EC2,
                severity=_assign_severity(cost, monthly_savings),
                reason=f"Low utilization detected ({metric_detail}). "
                       f"Instance type: {instance.get('instance_type', 'unknown')}.",
                recommended_action=(
                    "Consider downsizing to a smaller instance type "
                    "after reviewing workload requirements."
                ),
                current_monthly_cost=cost,
                estimated_optimized_monthly_cost=optimized_cost,
                estimated_monthly_savings=monthly_savings,
                estimated_annual_savings=round(monthly_savings * 12, 2),
            ))

    return findings


# ---------------------------------------------------------------------------
# EBS detection
# ---------------------------------------------------------------------------

def _detect_ebs_findings(ebs_data: list[dict]) -> list[OptimizationFinding]:
    """Detect optimization opportunities in EBS volumes."""
    findings: list[OptimizationFinding] = []

    for volume in ebs_data:
        volume_id = volume.get("volume_id", "unknown")
        cost = volume.get("monthly_cost", 0.0)
        size_gb = volume.get("size_gb", 0.0)
        used_gb = volume.get("used_gb", 0.0)
        status = volume.get("status", "")

        # --- Unattached volumes ---
        if status == "available":
            findings.append(OptimizationFinding(
                resource_id=volume_id,
                resource_type="EBS",
                issue_type=IssueType.UNATTACHED_EBS,
                severity=_assign_severity(cost, cost),
                reason=f"Volume is not attached to any instance "
                       f"({size_gb:.0f} GB, {volume.get('volume_type', 'unknown')}).",
                recommended_action=(
                    "Review whether this volume is still required. "
                    "Consider creating a snapshot and deleting the volume "
                    "if confirmed unused."
                ),
                current_monthly_cost=cost,
                estimated_optimized_monthly_cost=0.0,
                estimated_monthly_savings=cost,
                estimated_annual_savings=round(cost * 12, 2),
            ))
            continue

        # --- Underutilized volumes ---
        utilization = (used_gb / size_gb) if size_gb > 0 else 0.0

        if utilization < AnalysisThresholds.EBS_UTILIZATION_UNDERUTILIZED:
            # Estimate right-sized volume: used storage + headroom
            rightsized_gb = ceil(used_gb * MockPricing.EBS_RIGHTSIZING_HEADROOM)
            # Don't recommend a size larger than current
            rightsized_gb = min(rightsized_gb, size_gb)
            optimized_cost = round(rightsized_gb * MockPricing.EBS_COST_PER_GB_MONTH, 2)
            monthly_savings = round(max(cost - optimized_cost, 0.0), 2)

            findings.append(OptimizationFinding(
                resource_id=volume_id,
                resource_type="EBS",
                issue_type=IssueType.UNDERUTILIZED_EBS,
                severity=_assign_severity(cost, monthly_savings),
                reason=f"Low storage utilization: {used_gb:.0f}/{size_gb:.0f} GB "
                       f"({utilization:.0%}). "
                       f"Volume type: {volume.get('volume_type', 'unknown')}.",
                recommended_action=(
                    f"Consider reducing volume size to ~{rightsized_gb} GB "
                    f"after verifying workload requirements."
                ),
                current_monthly_cost=cost,
                estimated_optimized_monthly_cost=optimized_cost,
                estimated_monthly_savings=monthly_savings,
                estimated_annual_savings=round(monthly_savings * 12, 2),
            ))

    return findings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_findings(data: dict) -> list[OptimizationFinding]:
    """Run all waste-detection rules and return optimization findings.

    Args:
        data: Dict with 'ec2', 'ebs', 's3' resource lists.

    Returns:
        List of OptimizationFinding objects sorted by severity (HIGH first).
    """
    findings: list[OptimizationFinding] = []
    findings.extend(_detect_ec2_findings(data.get("ec2", [])))
    findings.extend(_detect_ebs_findings(data.get("ebs", [])))

    # S3: Our mock dataset only has bucket_name, region, storage_gb, and
    # monthly_cost. Without access-pattern or lifecycle-policy data we
    # cannot make meaningful optimisation recommendations. Intentionally
    # omitted to avoid fabricating certainty.

    # Sort: HIGH → MEDIUM → LOW, then by savings descending
    severity_order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    findings.sort(key=lambda f: (severity_order[f.severity], -f.estimated_monthly_savings))

    return findings
