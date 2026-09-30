"""Tests for Phase 5.8 Real AWS FinOps Analysis & Recommendation Integration."""

import pytest
from app import create_app
from app.extensions import db
from app.models import AnalysisRun, OptimizationFinding, Recommendation
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.resource_repository import ResourceRepository
from app.services.db_loader import load_data_from_db
from app.services.finops_analyzer import run_full_analysis
from app.services.recommendation_engine import ActionCategory, Confidence, generate_recommendations
from app.services.waste_detector import IssueType, Severity, detect_findings


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


class TestRealAWSFinOpsAnalysis:

    def test_real_aws_resource_can_be_analyzed(self, app):
        """1. Test that real AWS resource loaded from DB can be analyzed."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("i-00e59d865239b917b", "EC2", "ap-south-1", "running")
            ResourceRepository.upsert_metric(res.id, "cpu_utilization", 8.60)

            data = load_data_from_db()
            findings = detect_findings(data)

            assert len(findings) == 1
            assert findings[0].resource_id == "i-00e59d865239b917b"
            assert findings[0].issue_type == IssueType.UNDERUTILIZED_EC2

    def test_ec2_with_valid_low_cpu_produces_finding(self, app):
        """2. Test EC2 with valid low CPU produces appropriate finding."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("i-low-cpu", "EC2", "us-east-1", "running")
            ResourceRepository.upsert_metric(res.id, "cpu_utilization", 4.2)

            data = load_data_from_db()
            findings = detect_findings(data)

            assert len(findings) == 1
            assert findings[0].issue_type == IssueType.UNDERUTILIZED_EC2
            assert "CPU 4.2%" in findings[0].reason

    def test_ec2_with_cpu_zero_is_valid_data(self, app):
        """3. Test EC2 with CPU = 0.0 is treated as valid low CPU data."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("i-0a3e4fc72009455a6", "EC2", "ap-south-1", "running")
            ResourceRepository.upsert_metric(res.id, "cpu_utilization", 0.0)

            data = load_data_from_db()
            findings = detect_findings(data)

            assert len(findings) == 1
            assert findings[0].resource_id == "i-0a3e4fc72009455a6"
            assert findings[0].issue_type == IssueType.UNDERUTILIZED_EC2

    def test_ec2_with_cpu_none_does_not_produce_false_finding(self, app):
        """4. Test EC2 with CPU = None does not produce a false CPU underutilization finding."""
        with app.app_context():
            # Running instance without CloudWatch metric
            ResourceRepository.upsert_resource("i-no-cw-metric", "EC2", "ap-south-1", "running")

            data = load_data_from_db()
            findings = detect_findings(data)

            # Should NOT generate underutilization finding
            assert len(findings) == 0

    def test_stopped_ec2_behavior(self, app):
        """5. Test stopped EC2 behavior produces STOPPED_EC2 finding."""
        with app.app_context():
            ResourceRepository.upsert_resource("i-0ef43f7b106f255ee", "EC2", "ap-south-1", "stopped")

            data = load_data_from_db()
            findings = detect_findings(data)

            assert len(findings) == 1
            assert findings[0].resource_id == "i-0ef43f7b106f255ee"
            assert findings[0].issue_type == IssueType.STOPPED_EC2

    def test_account_level_cost_not_assigned_to_individual_resource(self, app):
        """6. Test that account-level cost is never assigned to an individual resource."""
        with app.app_context():
            acct = ResourceRepository.upsert_resource("AWS_ACCOUNT", "AWS_ACCOUNT", "global", "active")
            ResourceRepository.upsert_cost_record(acct.id, 999.99)

            ec2 = ResourceRepository.upsert_resource("i-clean", "EC2", "us-east-1", "running")
            ResourceRepository.upsert_metric(ec2.id, "cpu_utilization", 5.0)

            data = load_data_from_db()
            assert data["account_cost"] == 999.99
            assert data["ec2"][0]["monthly_cost"] == 0.0

            findings = detect_findings(data)
            assert findings[0].current_monthly_cost == 0.0  # Not 999.99!

    def test_missing_resource_cost_does_not_produce_fabricated_savings(self, app):
        """7. Test missing resource-level cost results in $0.00 / unavailable savings without fabrication."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("i-no-cost", "EC2", "us-east-1", "running")
            ResourceRepository.upsert_metric(res.id, "cpu_utilization", 3.0)

            data = load_data_from_db()
            findings = detect_findings(data)
            recs = generate_recommendations(findings)

            assert len(recs) == 1
            assert recs[0].current_monthly_cost == 0.0
            assert recs[0].estimated_monthly_savings == 0.0

    def test_findings_persisted_correctly(self, app):
        """8. Test findings are correctly persisted to database."""
        with app.app_context():
            run = AnalysisRepository.create_analysis_run()
            res = ResourceRepository.upsert_resource("i-test-persist", "EC2", "us-east-1", "stopped")

            saved_finding = AnalysisRepository.save_finding(
                analysis_run_id=run.id,
                resource_db_id=res.id,
                issue_type=IssueType.STOPPED_EC2.value,
                severity=Severity.LOW.value,
                savings=0.0,
                description="Instance is stopped",
            )

            assert saved_finding.id is not None
            db_finding = OptimizationFinding.query.filter_by(id=saved_finding.id).first()
            assert db_finding.issue_type == "STOPPED_EC2"

    def test_recommendations_generated_and_persisted_correctly(self, app):
        """9. Test recommendations are generated and persisted correctly."""
        with app.app_context():
            run = AnalysisRepository.create_analysis_run()
            res = ResourceRepository.upsert_resource("vol-test", "EBS", "us-east-1", "available")
            ResourceRepository.add_cost_record(res.id, 20.0)

            finding = AnalysisRepository.save_finding(
                analysis_run_id=run.id,
                resource_db_id=res.id,
                issue_type=IssueType.UNATTACHED_EBS.value,
                severity=Severity.HIGH.value,
                savings=20.0,
                description="Unattached volume",
            )

            rec = AnalysisRepository.save_recommendation(
                finding_id=finding.id,
                action_category=ActionCategory.REVIEW_AND_DELETE.value,
                recommendation_text="Delete volume",
                confidence=Confidence.HIGH.value,
                priority=1,
                savings=20.0,
            )

            assert rec.id is not None
            db_rec = Recommendation.query.filter_by(id=rec.id).first()
            assert db_rec.action_category == "REVIEW_AND_DELETE"

    def test_rerunning_analysis_idempotency_no_uncontrolled_duplicates(self, app):
        """10. Test re-running analysis idempotently saves findings for a run without duplicates."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("i-idem", "EC2", "us-east-1", "stopped")

            # First analysis run
            res1 = run_full_analysis()
            run1_id = res1["analysis_run"].id

            # Second analysis run
            res2 = run_full_analysis()
            run2_id = res2["analysis_run"].id

            assert run1_id != run2_id
            # Each run has exactly 1 finding
            run1_findings = OptimizationFinding.query.filter_by(analysis_run_id=run1_id).all()
            run2_findings = OptimizationFinding.query.filter_by(analysis_run_id=run2_id).all()

            assert len(run1_findings) == 1
            assert len(run2_findings) == 1

    def test_phase4_mock_data_tests_continue_passing(self, app):
        """11. Test that existing Phase 4 mock data pipeline continues working."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("i-phase4-mock", "EC2", "us-east-1", "running")
            ResourceRepository.add_cost_record(res.id, 100.0)
            ResourceRepository.add_metric(res.id, "cpu_utilization", 2.0)
            ResourceRepository.add_metric(res.id, "memory_utilization", 3.0)

            results = run_full_analysis()
            opt = results["optimization"]

            assert opt["total_monthly_savings"] == 50.0  # 50% of 100.0
            assert opt["total_opportunities"] == 1

    def test_complete_postgresql_db_loader_finops_engine_flow(self, app):
        """12. Complete PostgreSQL -> db_loader -> FinOps engine flow works end-to-end."""
        with app.app_context():
            # Account cost
            acct = ResourceRepository.upsert_resource("AWS_ACCOUNT", "AWS_ACCOUNT", "global", "active")
            ResourceRepository.upsert_cost_record(acct.id, 120.0)

            # Discovered real EC2
            res1 = ResourceRepository.upsert_resource("i-real-1", "EC2", "ap-south-1", "running")
            ResourceRepository.upsert_metric(res1.id, "cpu_utilization", 5.0)

            # Discovered real EBS
            res2 = ResourceRepository.upsert_resource("vol-real-1", "EBS", "ap-south-1", "available")
            ResourceRepository.add_cost_record(res2.id, 10.0)

            results = run_full_analysis()

            assert results["summary"]["total_resources"] == 2
            assert results["summary"]["costs"]["account_cost"] == 120.0
            assert results["persisted_findings_count"] == 2
            assert len(results["recommendations"]) == 2
