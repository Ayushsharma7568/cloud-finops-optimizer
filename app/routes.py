import logging
from flask import render_template

from app.services.db_loader import load_data_from_db
from app.services.cost_analysis import generate_summary
from app.services.waste_detector import detect_findings
from app.services.recommendation_engine import generate_recommendations
from app.services.savings_calculator import generate_optimization_summary
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.resource_repository import ResourceRepository

logger = logging.getLogger(__name__)

def register_routes(app):
    """Register all application routes."""

    @app.route("/")
    def index():
        try:
            # 1. Start Analysis Run
            run = AnalysisRepository.create_analysis_run()

            # 2. Load Resources from DB
            data = load_data_from_db()
            summary = generate_summary(data)

            # 3. Run Analysis
            findings = detect_findings(data)
            recommendations = generate_recommendations(findings)
            optimization = generate_optimization_summary(
                recommendations, summary["costs"]["total"]
            )

            # 4. Persist Findings & Recommendations
            # This requires looking up the resource_id internally.
            for rec in recommendations:
                # Find DB resource id
                res_external_id = rec.resource_id
                res_db = ResourceRepository.get_resource_by_external_id(res_external_id)
                if res_db:
                    saved_finding = AnalysisRepository.save_finding(
                        analysis_run_id=run.id,
                        resource_db_id=res_db.id,
                        issue_type=rec.issue_type,
                        severity=rec.severity.name,
                        savings=rec.estimated_monthly_savings,
                        description=rec.reason
                    )
                    
                    AnalysisRepository.save_recommendation(
                        finding_id=saved_finding.id,
                        action_category=rec.action_category.name,
                        recommendation_text=rec.recommendation,
                        confidence=rec.confidence.name,
                        priority=rec.priority,
                        savings=rec.estimated_monthly_savings
                    )

            # 5. Complete Analysis Run
            AnalysisRepository.complete_analysis_run(
                run_id=run.id,
                resource_count=summary["total_resources"],
                total_cost=summary["costs"]["total"],
                potential_savings=optimization["total_monthly_savings"]
            )

            error = None
        except Exception as e:
            logger.error("Failed to run analysis: %s", e)
            summary = None
            optimization = None
            error = str(e)

        return render_template(
            "index.html",
            summary=summary,
            optimization=optimization,
            error=error,
        )

