from datetime import datetime
from app.extensions import db
from app.models import AnalysisRun, OptimizationFinding, Recommendation


class AnalysisRepository:
    """Repository for handling database operations for analysis runs, findings, and recommendations."""

    @staticmethod
    def create_analysis_run():
        """Create a new analysis run record in RUNNING status."""
        run = AnalysisRun(status="RUNNING")
        db.session.add(run)
        db.session.commit()
        return run

    @staticmethod
    def complete_analysis_run(run_id, resource_count, total_cost, potential_savings, status="SUCCESS"):
        """Mark an analysis run as complete and update metrics."""
        run = db.session.get(AnalysisRun, run_id) if hasattr(db.session, 'get') else AnalysisRun.query.get(run_id)
        if run:
            run.completed_at = datetime.utcnow()
            run.status = status
            run.resource_count = resource_count
            run.total_monthly_cost = total_cost
            run.potential_monthly_savings = potential_savings
            db.session.commit()
        return run

    @staticmethod
    def fail_analysis_run(run_id, error_message, status="FAILED"):
        """Mark an analysis run as FAILED and record error message."""
        run = db.session.get(AnalysisRun, run_id) if hasattr(db.session, 'get') else AnalysisRun.query.get(run_id)
        if run:
            run.completed_at = datetime.utcnow()
            run.status = status
            run.error_message = str(error_message)
            db.session.commit()
        return run

    @staticmethod
    def get_latest_analysis_run():
        """Get the most recent successful or completed analysis run."""
        return (
            AnalysisRun.query.filter(AnalysisRun.status.in_(["SUCCESS", "COMPLETED"]))
            .order_by(AnalysisRun.started_at.desc())
            .first()
        )

    @staticmethod
    def get_recent_analysis_runs(limit=10):
        """Retrieve recent analysis runs ordered from newest to oldest."""
        return AnalysisRun.query.order_by(AnalysisRun.started_at.desc()).limit(limit).all()

    @staticmethod
    def get_analysis_run_by_id(run_id):
        """Retrieve a specific analysis run by its primary key ID."""
        if hasattr(db.session, 'get'):
            return db.session.get(AnalysisRun, run_id)
        return AnalysisRun.query.get(run_id)

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
