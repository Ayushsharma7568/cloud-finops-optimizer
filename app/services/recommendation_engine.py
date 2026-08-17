"""Recommendation engine — generates actionable optimization recommendations.

Consumes OptimizationFinding objects from Phase 2 and produces structured
Recommendation objects with explicit actions, confidence, and explanations.
"""

from dataclasses import dataclass
from enum import Enum
import re

from app.services.waste_detector import OptimizationFinding, IssueType, Severity


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActionCategory(str, Enum):
    """Standardized categories for recommended actions."""

    DOWNSIZE = "DOWNSIZE"
    REVIEW_AND_TERMINATE = "REVIEW_AND_TERMINATE"
    RESIZE_STORAGE = "RESIZE_STORAGE"
    REVIEW_AND_DELETE = "REVIEW_AND_DELETE"


class Confidence(str, Enum):
    """Confidence level of the recommendation based on available mock data."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ---------------------------------------------------------------------------
# Data Structure
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    """A structured optimization recommendation."""

    resource_id: str
    resource_type: str
    issue_type: IssueType
    severity: Severity
    confidence: Confidence
    reason: str
    recommendation: str
    action_category: ActionCategory
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
            "confidence": self.confidence.value,
            "reason": self.reason,
            "recommendation": self.recommendation,
            "action_category": self.action_category.value,
            "current_monthly_cost": self.current_monthly_cost,
            "estimated_optimized_monthly_cost": self.estimated_optimized_monthly_cost,
            "estimated_monthly_savings": self.estimated_monthly_savings,
            "estimated_annual_savings": self.estimated_annual_savings,
        }


# ---------------------------------------------------------------------------
# Recommendation Generators
# ---------------------------------------------------------------------------

def _extract_instance_type(reason: str) -> str:
    """Helper to extract instance type from the finding reason."""
    match = re.search(r"Instance type:\s*([^\.]+.[^\.]+)", reason)
    return match.group(1).strip('.') if match else "unknown"


def _generate_ec2_underutilized(finding: OptimizationFinding) -> Recommendation:
    """Generate recommendation for UNDERUTILIZED_EC2."""
    instance_type = _extract_instance_type(finding.reason)
    
    # We don't have exact target mapping, but we can make a generalized suggestion
    recommendation_text = (
        f"Consider downsizing from {instance_type} to a smaller instance type "
        "after reviewing workload requirements."
    )
    
    return Recommendation(
        resource_id=finding.resource_id,
        resource_type=finding.resource_type,
        issue_type=finding.issue_type,
        severity=finding.severity,
        confidence=Confidence.MEDIUM,  # Medium confidence for utilization without long history
        reason=f"EC2 instance is significantly underutilized. {finding.reason}",
        recommendation=recommendation_text,
        action_category=ActionCategory.DOWNSIZE,
        current_monthly_cost=finding.current_monthly_cost,
        estimated_optimized_monthly_cost=finding.estimated_optimized_monthly_cost,
        estimated_monthly_savings=finding.estimated_monthly_savings,
        estimated_annual_savings=finding.estimated_annual_savings,
    )


def _generate_ec2_stopped(finding: OptimizationFinding) -> Recommendation:
    """Generate recommendation for STOPPED_EC2."""
    return Recommendation(
        resource_id=finding.resource_id,
        resource_type=finding.resource_type,
        issue_type=finding.issue_type,
        severity=finding.severity,
        confidence=Confidence.HIGH,  # High confidence since the state is explicitly stopped
        reason="EC2 instance is stopped but continues to incur costs for associated resources (e.g., EBS).",
        recommendation="Review whether the instance is still required. If confirmed unused, consider terminating it.",
        action_category=ActionCategory.REVIEW_AND_TERMINATE,
        current_monthly_cost=finding.current_monthly_cost,
        estimated_optimized_monthly_cost=finding.estimated_optimized_monthly_cost,
        estimated_monthly_savings=finding.estimated_monthly_savings,
        estimated_annual_savings=finding.estimated_annual_savings,
    )


def _generate_ebs_underutilized(finding: OptimizationFinding) -> Recommendation:
    """Generate recommendation for UNDERUTILIZED_EBS."""
    return Recommendation(
        resource_id=finding.resource_id,
        resource_type=finding.resource_type,
        issue_type=finding.issue_type,
        severity=finding.severity,
        confidence=Confidence.MEDIUM,
        reason=f"EBS volume has low storage utilization. {finding.reason}",
        recommendation=finding.recommended_action,
        action_category=ActionCategory.RESIZE_STORAGE,
        current_monthly_cost=finding.current_monthly_cost,
        estimated_optimized_monthly_cost=finding.estimated_optimized_monthly_cost,
        estimated_monthly_savings=finding.estimated_monthly_savings,
        estimated_annual_savings=finding.estimated_annual_savings,
    )


def _generate_ebs_unattached(finding: OptimizationFinding) -> Recommendation:
    """Generate recommendation for UNATTACHED_EBS."""
    return Recommendation(
        resource_id=finding.resource_id,
        resource_type=finding.resource_type,
        issue_type=finding.issue_type,
        severity=finding.severity,
        confidence=Confidence.HIGH,
        reason=f"EBS volume is currently unattached. {finding.reason}",
        recommendation="Review whether the volume is still required. If confirmed unused, consider deleting it (take a snapshot first if needed).",
        action_category=ActionCategory.REVIEW_AND_DELETE,
        current_monthly_cost=finding.current_monthly_cost,
        estimated_optimized_monthly_cost=finding.estimated_optimized_monthly_cost,
        estimated_monthly_savings=finding.estimated_monthly_savings,
        estimated_annual_savings=finding.estimated_annual_savings,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prioritize_recommendations(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Sort recommendations by impact.
    
    1. HIGH before MEDIUM before LOW severity.
    2. Higher estimated monthly savings first.
    """
    severity_order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    
    # Sort in place
    recommendations.sort(
        key=lambda r: (severity_order[r.severity], -r.estimated_monthly_savings)
    )
    return recommendations


def generate_recommendations(findings: list[OptimizationFinding]) -> list[Recommendation]:
    """Transform optimization findings into structured recommendations."""
    recommendations = []
    
    # Mapping issue types to generator functions
    generators = {
        IssueType.UNDERUTILIZED_EC2: _generate_ec2_underutilized,
        IssueType.STOPPED_EC2: _generate_ec2_stopped,
        IssueType.UNDERUTILIZED_EBS: _generate_ebs_underutilized,
        IssueType.UNATTACHED_EBS: _generate_ebs_unattached,
    }
    
    for finding in findings:
        generator = generators.get(finding.issue_type)
        if generator:
            rec = generator(finding)
            recommendations.append(rec)
            
    return prioritize_recommendations(recommendations)
