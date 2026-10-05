"""FinOps Reporting Service.

Converts database AnalysisRun, OptimizationFinding, and Recommendation objects
into structured application-level reports and summaries for API endpoints & CLI verification.
"""

import logging
from app.repositories.analysis_repository import AnalysisRepository
from app.services.db_loader import load_data_from_db

logger = logging.getLogger(__name__)


def format_analysis_run_summary(run) -> dict:
    """Format an AnalysisRun database model into a clean summary dictionary."""
    if not run:
        return {}

    findings_count = len(run.findings) if run.findings else 0
    recs_count = 0
    savings_available = 0
    savings_unavailable = 0
    findings_list = []

    if run.findings:
        for f in run.findings:
            recs_count += len(f.recommendations) if f.recommendations else 0
            if f.estimated_monthly_savings and f.estimated_monthly_savings > 0:
                savings_available += 1
            else:
                savings_unavailable += 1

            recs = []
            if f.recommendations:
                for r in f.recommendations:
                    recs.append({
                        "id": r.id,
                        "action_category": r.action_category,
                        "recommendation_text": r.recommendation_text,
                        "confidence": r.confidence,
                        "priority": r.priority,
                        "estimated_monthly_savings": r.estimated_monthly_savings,
                    })

            findings_list.append({
                "id": f.id,
                "resource_id": f.resource.resource_id if f.resource else f"Res #{f.resource_id}",
                "resource_type": f.resource.resource_type if f.resource else "AWS",
                "issue_type": f.issue_type,
                "severity": f.severity,
                "description": f.description,
                "estimated_monthly_savings": f.estimated_monthly_savings,
                "recommendations": recs,
            })

    return {
        "id": run.id,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "status": run.status,
        "resource_count": run.resource_count,
        "total_monthly_cost": run.total_monthly_cost,
        "potential_monthly_savings": run.potential_monthly_savings,
        "error_message": run.error_message,
        "findings_count": findings_count,
        "recommendations_count": recs_count,
        "savings_available_count": savings_available,
        "savings_unavailable_count": savings_unavailable,
        "findings": findings_list,
    }


def get_latest_analysis_summary() -> dict | None:
    """Get formatted summary of the latest successful analysis run."""
    run = AnalysisRepository.get_latest_analysis_run()
    if not run:
        return None
    return format_analysis_run_summary(run)


def get_analysis_run_summary_by_id(run_id: int) -> dict | None:
    """Get formatted summary of a specific analysis run by ID."""
    run = AnalysisRepository.get_analysis_run_by_id(run_id)
    if not run:
        return None
    return format_analysis_run_summary(run)


def get_recent_analysis_history(limit: int = 10) -> list[dict]:
    """Retrieve history of recent analysis runs ordered from newest to oldest."""
    runs = AnalysisRepository.get_recent_analysis_runs(limit=limit)
    return [format_analysis_run_summary(run) for run in runs]
