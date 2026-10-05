"""Tests for Phase 5.9 FinOps Analysis Runs & Reporting."""

from datetime import datetime, timedelta
import pytest

from app import create_app
from app.extensions import db
from app.models import AnalysisRun, OptimizationFinding, Recommendation
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.resource_repository import ResourceRepository
from app.services.finops_analyzer import run_full_analysis
from app.services.finops_reporting import (
    format_analysis_run_summary,
    get_analysis_run_summary_by_id,
    get_latest_analysis_summary,
    get_recent_analysis_history,
)


@pytest.fixture
def app():
    """Create a Flask app with an in-memory SQLite DB for testing."""
    test_config = {"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "TESTING": True}
    app_inst = create_app(test_config=test_config)

    with app_inst.app_context():
        db.create_all()
        yield app_inst
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


class TestFinOpsAnalysisRunsAndReporting:

    def test_analysis_run_creation_success(self, app):
        """1. Test creation of AnalysisRun in RUNNING status."""
        with app.app_context():
            run = AnalysisRepository.create_analysis_run()
            assert run.id is not None
            assert run.status == "RUNNING"
            assert run.started_at is not None
            assert run.completed_at is None

    def test_analysis_run_completion_success(self, app):
        """2. Test successful completion of AnalysisRun."""
        with app.app_context():
            run = AnalysisRepository.create_analysis_run()
            completed = AnalysisRepository.complete_analysis_run(
                run.id, resource_count=10, total_cost=100.0, potential_savings=25.0
            )

            assert completed.status == "SUCCESS"
            assert completed.completed_at is not None
            assert completed.resource_count == 10
            assert completed.total_monthly_cost == 100.0
            assert completed.potential_monthly_savings == 25.0

    def test_failed_analysis_marks_run_failed(self, app):
        """3 & 4. Test failed analysis marks run as FAILED and preserves error_message."""
        with app.app_context():
            run = AnalysisRepository.create_analysis_run()
            failed = AnalysisRepository.fail_analysis_run(
                run.id, error_message="Database connection error"
            )

            assert failed.status == "FAILED"
            assert failed.completed_at is not None
            assert failed.error_message == "Database connection error"

    def test_analysis_summary_generation(self, app):
        """5. Test formatting AnalysisRun summary dictionary."""
        with app.app_context():
            run = AnalysisRepository.create_analysis_run()
            res = ResourceRepository.upsert_resource("i-sum", "EC2", "us-east-1", "stopped")

            finding = AnalysisRepository.save_finding(
                run.id, res.id, "STOPPED_EC2", "LOW", 0.0, "Stopped instance"
            )
            AnalysisRepository.save_recommendation(
                finding.id, "REVIEW_AND_TERMINATE", "Terminate instance", "HIGH", 1, 0.0
            )
            completed = AnalysisRepository.complete_analysis_run(run.id, 1, 0.0, 0.0)

            summary = format_analysis_run_summary(completed)

            assert summary["id"] == run.id
            assert summary["status"] == "SUCCESS"
            assert summary["resource_count"] == 1
            assert summary["findings_count"] == 1
            assert summary["recommendations_count"] == 1
            assert summary["savings_unavailable_count"] == 1
            assert summary["savings_available_count"] == 0

    def test_latest_analysis_retrieval(self, app):
        """6. Test retrieving latest successful analysis run."""
        with app.app_context():
            run1 = AnalysisRepository.create_analysis_run()
            AnalysisRepository.complete_analysis_run(run1.id, 5, 50.0, 10.0)

            run2 = AnalysisRepository.create_analysis_run()
            AnalysisRepository.complete_analysis_run(run2.id, 8, 80.0, 20.0)

            latest = AnalysisRepository.get_latest_analysis_run()
            assert latest.id == run2.id
            assert latest.resource_count == 8

            summary = get_latest_analysis_summary()
            assert summary["id"] == run2.id

    def test_recent_analysis_history_retrieval_and_ordering(self, app):
        """7 & 8. Test history retrieval is ordered from newest to oldest."""
        with app.app_context():
            run1 = AnalysisRepository.create_analysis_run()
            AnalysisRepository.complete_analysis_run(run1.id, 5, 50.0, 10.0)

            run2 = AnalysisRepository.create_analysis_run()
            AnalysisRepository.complete_analysis_run(run2.id, 8, 80.0, 20.0)

            history = get_recent_analysis_history(limit=10)
            assert len(history) == 2
            # Order must be newest first (run2 then run1)
            assert history[0]["id"] == run2.id
            assert history[1]["id"] == run1.id

    def test_separate_analysis_runs_retain_separate_results(self, app):
        """9 & 10. Test separate runs retain separate findings/recommendations idempotently."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("i-sep", "EC2", "us-east-1", "stopped")

            # Run 1
            out1 = run_full_analysis()
            run1_id = out1["analysis_run"].id

            # Run 2
            out2 = run_full_analysis()
            run2_id = out2["analysis_run"].id

            f1 = OptimizationFinding.query.filter_by(analysis_run_id=run1_id).all()
            f2 = OptimizationFinding.query.filter_by(analysis_run_id=run2_id).all()

            assert len(f1) == 1
            assert len(f2) == 1
            assert f1[0].id != f2[0].id

    def test_missing_savings_unavailable_and_account_cost_separate(self, app):
        """11 & 12. Test missing savings remain unavailable ($0.0) and account cost separate."""
        with app.app_context():
            acct = ResourceRepository.upsert_resource("AWS_ACCOUNT", "AWS_ACCOUNT", "global", "active")
            ResourceRepository.upsert_cost_record(acct.id, 500.0)

            res = ResourceRepository.upsert_resource("i-no-cost-res", "EC2", "ap-south-1", "running")
            ResourceRepository.upsert_metric(res.id, "cpu_utilization", 2.0)

            out = run_full_analysis()
            summary = out["summary"]
            recs = out["recommendations"]

            assert summary["costs"]["account_cost"] == 500.0
            assert summary["costs"]["ec2"] == 0.0
            assert len(recs) == 1
            assert recs[0].estimated_monthly_savings == 0.0

    def test_api_endpoints_behavior(self, client, app):
        """14. Test GET /api/analysis/latest, /api/analysis/history, /api/analysis/<id>."""
        with app.app_context():
            # Before any runs exist
            res_404 = client.get("/api/analysis/latest")
            assert res_404.status_code == 404

            # Run analysis
            out = run_full_analysis()
            run_id = out["analysis_run"].id

            # GET /api/analysis/latest
            res_latest = client.get("/api/analysis/latest")
            assert res_latest.status_code == 200
            json_latest = res_latest.get_json()
            assert json_latest["id"] == run_id
            assert json_latest["status"] == "SUCCESS"

            # GET /api/analysis/history
            res_hist = client.get("/api/analysis/history")
            assert res_hist.status_code == 200
            json_hist = res_hist.get_json()
            assert len(json_hist) >= 1
            assert json_hist[0]["id"] == run_id

            # GET /api/analysis/<id>
            res_id = client.get(f"/api/analysis/{run_id}")
            assert res_id.status_code == 200
            json_id = res_id.get_json()
            assert json_id["id"] == run_id

            # GET invalid ID
            res_inv = client.get("/api/analysis/999999")
            assert res_inv.status_code == 404
