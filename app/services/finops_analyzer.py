"""FinOps Analysis Orchestrator Service.

Coordinates loading DB FinOps data, running waste detection, generating recommendations,
calculating savings, and persisting results to PostgreSQL via AnalysisRepository.
"""

import logging
from app.services.db_loader import load_data_from_db
from app.services.cost_analysis import generate_summary
from app.services.waste_detector import detect_findings
from app.services.recommendation_engine import generate_recommendations
from app.services.savings_calculator import generate_optimization_summary
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.resource_repository import ResourceRepository

logger = logging.getLogger(__name__)


def run_full_analysis() -> dict:
    """Run full FinOps analysis workflow against PostgreSQL database data.

    Returns:
        dict: Summary of analysis run containing run model, summary metrics,
              findings, recommendations, and optimization metrics.
    """
    logger.info("Starting FinOps analysis run...")

    # 1. Create AnalysisRun record in DB
    run = AnalysisRepository.create_analysis_run()

    # 2. Load unified FinOps context from DB
    data = load_data_from_db()
    summary = generate_summary(data)

    # 3. Detect waste findings and generate recommendations
    findings = detect_findings(data)
    recommendations = generate_recommendations(findings)
    optimization = generate_optimization_summary(
        recommendations, summary["costs"]["total"]
    )

    # 4. Persist findings & recommendations in DB idempotently
    persisted_findings = 0
    persisted_recommendations = 0

    for rec in recommendations:
        res_db = ResourceRepository.get_resource_by_external_id(rec.resource_id)
        if res_db:
            issue_val = getattr(rec.issue_type, "value", str(rec.issue_type))
            sev_val = getattr(rec.severity, "value", str(rec.severity))
            action_val = getattr(rec.action_category, "value", str(rec.action_category))
            conf_val = getattr(rec.confidence, "value", str(rec.confidence))

            saved_finding = AnalysisRepository.save_finding(
                analysis_run_id=run.id,
                resource_db_id=res_db.id,
                issue_type=issue_val,
                severity=sev_val,
                savings=rec.estimated_monthly_savings,
                description=rec.reason,
            )
            persisted_findings += 1

            AnalysisRepository.save_recommendation(
                finding_id=saved_finding.id,
                action_category=action_val,
                recommendation_text=rec.recommendation,
                confidence=conf_val,
                priority=rec.priority,
                savings=rec.estimated_monthly_savings,
            )
            persisted_recommendations += 1

    # 5. Complete AnalysisRun record
    completed_run = AnalysisRepository.complete_analysis_run(
        run_id=run.id,
        resource_count=summary["total_resources"],
        total_cost=summary["costs"]["total"],
        potential_savings=optimization["total_monthly_savings"],
    )

    logger.info(
        "FinOps analysis run #%d completed successfully. Processed %d resources, %d findings persisted.",
        completed_run.id,
        summary["total_resources"],
        persisted_findings,
    )

    return {
        "analysis_run": completed_run,
        "summary": summary,
        "findings": findings,
        "recommendations": recommendations,
        "optimization": optimization,
        "data": data,
        "persisted_findings_count": persisted_findings,
        "persisted_recommendations_count": persisted_recommendations,
    }
