"""Savings calculator — aggregates estimated savings from optimization findings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.waste_detector import OptimizationFinding


def calculate_savings_by_service(
    findings: list[OptimizationFinding],
) -> dict[str, float]:
    """Sum estimated monthly savings grouped by resource type.

    Returns:
        Dict mapping resource type (e.g., 'EC2', 'EBS') to total monthly savings.
    """
    by_service: dict[str, float] = {}
    for f in findings:
        by_service[f.resource_type] = round(
            by_service.get(f.resource_type, 0.0) + f.estimated_monthly_savings, 2
        )
    return by_service


def generate_optimization_summary(
    findings: list[OptimizationFinding],
    total_monthly_cost: float,
) -> dict:
    """Produce a complete optimization summary.

    Args:
        findings: List of OptimizationFinding objects from the waste detector.
        total_monthly_cost: Current total monthly cloud spend.

    Returns:
        Dict containing all optimization metrics for the dashboard.
    """
    total_monthly_savings = round(
        sum(f.estimated_monthly_savings for f in findings), 2
    )
    total_annual_savings = round(total_monthly_savings * 12, 2)

    high_count = sum(1 for f in findings if f.severity.value == "HIGH")

    savings_pct = (
        round(total_monthly_savings / total_monthly_cost * 100, 1)
        if total_monthly_cost > 0
        else 0.0
    )

    savings_by_service = calculate_savings_by_service(findings)

    return {
        "total_monthly_savings": total_monthly_savings,
        "total_annual_savings": total_annual_savings,
        "savings_percentage": savings_pct,
        "total_opportunities": len(findings),
        "high_severity_count": high_count,
        "savings_by_service": savings_by_service,
        "findings": [f.to_dict() for f in findings],
    }
