from datetime import datetime
from app.extensions import db
from app.models import AnalysisRun, OptimizationFinding, Recommendation


class AnalysisRepository:
    """Repository for handling database operations for analysis runs, findings, and recommendations."""

    @staticmethod
    def create_analysis_run():
        """Create a new analysis run record."""
        run = AnalysisRun(status="RUNNING")
        db.session.add(run)
        db.session.commit()
        return run

    @staticmethod
    def complete_analysis_run(run_id, resource_count, total_cost, potential_savings, status="SUCCESS"):
        """Mark an analysis run as complete and update metrics."""
        run = AnalysisRun.query.get(run_id)
        if run:
            run.completed_at = datetime.utcnow()
            run.status = status
            run.resource_count = resource_count
            run.total_monthly_cost = total_cost
            run.potential_monthly_savings = potential_savings
            db.session.commit()
        return run

    @staticmethod
    def get_latest_analysis_run():
        """Get the most recent successful analysis run."""
        return AnalysisRun.query.filter_by(status="SUCCESS").order_by(AnalysisRun.started_at.desc()).first()

    @staticmethod
    def save_finding(analysis_run_id, resource_db_id, issue_type, severity, savings, description):
        """Save a waste detection finding idempotently for a given analysis run."""
        finding = OptimizationFinding.query.filter_by(
            analysis_run_id=analysis_run_id,
            resource_id=resource_db_id,
            issue_type=str(issue_type)
        ).first()

        if not finding:
            finding = OptimizationFinding(
                analysis_run_id=analysis_run_id,
                resource_id=resource_db_id,
                issue_type=str(issue_type),
                severity=str(severity),
                estimated_monthly_savings=savings,
                description=description
            )
            db.session.add(finding)
            db.session.commit()
        return finding

    @staticmethod
    def save_recommendation(finding_id, action_category, recommendation_text, confidence, priority, savings):
        """Save a recommendation linked to a finding idempotently."""
        recommendation = Recommendation.query.filter_by(
            finding_id=finding_id,
            action_category=str(action_category)
        ).first()

        if not recommendation:
            recommendation = Recommendation(
                finding_id=finding_id,
                action_category=str(action_category),
                recommendation_text=recommendation_text,
                confidence=str(confidence),
                priority=priority,
                estimated_monthly_savings=savings
            )
            db.session.add(recommendation)
            db.session.commit()
        return recommendation
