"""Savings calculator — aggregates estimated savings from optimization recommendations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Union
from collections import Counter

if TYPE_CHECKING:
    from app.services.waste_detector import OptimizationFinding
    from app.services.recommendation_engine import Recommendation

# We use a type union to support both Phase 2 findings and Phase 3 recommendations
OptItem = Union['OptimizationFinding', 'Recommendation']

def calculate_savings_by_service(
    items: list[OptItem],
) -> dict[str, float]:
    """Sum estimated monthly savings grouped by resource type.

    Returns:
        Dict mapping resource type (e.g., 'EC2', 'EBS') to total monthly savings.
    """
    by_service: dict[str, float] = {}
    for f in items:
        by_service[f.resource_type] = round(
            by_service.get(f.resource_type, 0.0) + f.estimated_monthly_savings, 2
        )
    return by_service


def generate_optimization_summary(
    items: list[OptItem],
    total_monthly_cost: float,
) -> dict:
    """Produce a complete optimization summary.

    Args:
        items: List of OptimizationFinding or Recommendation objects.
        total_monthly_cost: Current total monthly cloud spend.

    Returns:
        Dict containing all optimization metrics for the dashboard.
    """
    total_monthly_savings = round(
        sum(f.estimated_monthly_savings for f in items), 2
    )
    total_annual_savings = round(total_monthly_savings * 12, 2)

    # Base counts
    high_count = sum(1 for f in items if getattr(f.severity, 'value', f.severity) == "HIGH")
    medium_count = sum(1 for f in items if getattr(f.severity, 'value', f.severity) == "MEDIUM")
    low_count = sum(1 for f in items if getattr(f.severity, 'value', f.severity) == "LOW")

    savings_pct = (
        round(total_monthly_savings / total_monthly_cost * 100, 1)
        if total_monthly_cost > 0
        else 0.0
    )

    savings_by_service = calculate_savings_by_service(items)

    # Recommendation specific logic
    action_counts = {}
    top_recommendation = None
    if items and hasattr(items[0], 'action_category'):
        # It's a list of Recommendations
        actions = [getattr(r.action_category, 'value', r.action_category) for r in items]
        action_counts = dict(Counter(actions))
        top_recommendation = items[0].to_dict() if items else None
        
    return {
        "total_monthly_savings": total_monthly_savings,
        "total_annual_savings": total_annual_savings,
        "savings_percentage": savings_pct,
        "total_opportunities": len(items),
        "high_severity_count": high_count,
        "medium_severity_count": medium_count,
        "low_severity_count": low_count,
        "savings_by_service": savings_by_service,
        "action_counts": action_counts,
        "top_recommendation": top_recommendation,
        "findings": [f.to_dict() for f in items],
    }
