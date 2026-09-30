"""Tests for Phase 5.7 FinOps Data Correlation & Unification Layer."""

from datetime import datetime
import pytest

from app import create_app
from app.extensions import db
from app.repositories.resource_repository import ResourceRepository
from app.services.cost_analysis import generate_summary
from app.services.db_loader import load_data_from_db, load_finops_correlation_summary
from app.services.recommendation_engine import generate_recommendations
from app.services.waste_detector import detect_findings


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


class TestFinOpsDataCorrelation:

    def test_real_aws_resource_and_cpu_metric_loaded_together(self, app):
        """1. Test that real AWS resource and its CloudWatch CPU metric are loaded together."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("i-00e59d865239b917b", "EC2", "ap-south-1", "running")
            ResourceRepository.upsert_metric(res.id, "cpu_utilization", 8.60)

            data = load_data_from_db()
            assert len(data["ec2"]) == 1
            ec2_item = data["ec2"][0]
            assert ec2_item["resource_id"] == "i-00e59d865239b917b"
            assert ec2_item["cpu_utilization"] == 8.60

    def test_missing_cloudwatch_metric_remains_none(self, app):
        """2. Test that missing CloudWatch metric remains None and does not become 0.0."""
        with app.app_context():
            ResourceRepository.upsert_resource("i-0ef43f7b106f255ee", "EC2", "ap-south-1", "stopped")

            data = load_data_from_db()
            assert len(data["ec2"]) == 1
            ec2_item = data["ec2"][0]
            assert ec2_item["cpu_utilization"] is None
            assert ec2_item["memory_utilization"] is None

    def test_account_level_cost_remains_account_level(self, app):
        """3. Test that account-level cost is preserved separately as account_cost."""
        with app.app_context():
            account_res = ResourceRepository.upsert_resource("AWS_ACCOUNT", "AWS_ACCOUNT", "global", "active")
            ResourceRepository.upsert_cost_record(account_res.id, 100.50, recorded_at=datetime(2026, 9, 29))

            data = load_data_from_db()
            assert data["account_cost"] == 100.50
            assert len(data["account_cost_records"]) == 1
            assert data["account_cost_records"][0]["monthly_cost"] == 100.50

    def test_account_level_cost_not_attached_to_ec2(self, app):
        """4. Test that account-level cost is NOT incorrectly attached to an EC2 resource."""
        with app.app_context():
            account_res = ResourceRepository.upsert_resource("AWS_ACCOUNT", "AWS_ACCOUNT", "global", "active")
            ResourceRepository.upsert_cost_record(account_res.id, 500.00)

            ec2_res = ResourceRepository.upsert_resource("i-0a3e4fc72009455a6", "EC2", "ap-south-1", "running")
            ResourceRepository.upsert_metric(ec2_res.id, "cpu_utilization", 0.0)

            summary = load_finops_correlation_summary()
            data = summary["data"]

            assert summary["account_cost_preserved_separately"] is True
            assert summary["fake_resource_costs_detected"] is False

            ec2_item = data["ec2"][0]
            assert ec2_item["resource_id"] == "i-0a3e4fc72009455a6"
            assert ec2_item["monthly_cost"] == 0.0  # Not 500.0!

    def test_multiple_resources_coexist_with_account_cost(self, app):
        """5. Test that multiple resources coexist cleanly with one account-level cost record."""
        with app.app_context():
            account_res = ResourceRepository.upsert_resource("AWS_ACCOUNT", "AWS_ACCOUNT", "global", "active")
            ResourceRepository.upsert_cost_record(account_res.id, 25.0)

            ResourceRepository.upsert_resource("i-ec2-1", "EC2", "us-east-1", "running")
            ResourceRepository.upsert_resource("i-ec2-2", "EC2", "us-east-1", "stopped")
            ResourceRepository.upsert_resource("vol-ebs-1", "EBS", "us-east-1", "available")

            data = load_data_from_db()
            assert len(data["ec2"]) == 2
            assert len(data["ebs"]) == 1
            assert data["account_cost"] == 25.0
            assert data["summary_metrics"]["total_resources"] == 3

    def test_existing_phase4_mock_data_backward_compatibility(self, app):
        """6. Test that existing Phase 4 mock resource costs continue working."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("i-mock-1", "EC2", "us-east-1", "running")
            ResourceRepository.add_cost_record(res.id, 45.0)
            ResourceRepository.add_metric(res.id, "cpu_utilization", 4.0)
            ResourceRepository.add_metric(res.id, "memory_utilization", 5.0)

            data = load_data_from_db()
            assert data["ec2"][0]["monthly_cost"] == 45.0
            assert data["ec2"][0]["cpu_utilization"] == 4.0

            findings = detect_findings(data)
            assert len(findings) == 1
            assert findings[0].estimated_monthly_savings > 0

    def test_recommendations_and_findings_not_broken(self, app):
        """7. Test that recommendations and findings generation pipeline works seamlessly."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("vol-unattached", "EBS", "us-east-1", "available")
            ResourceRepository.add_cost_record(res.id, 15.0)

            data = load_data_from_db()
            findings = detect_findings(data)
            recs = generate_recommendations(findings)

            assert len(findings) == 1
            assert len(recs) == 1
            assert recs[0].resource_id == "vol-unattached"
            assert recs[0].action_category == "REVIEW_AND_DELETE"

    def test_empty_database_behavior(self, app):
        """8. Test empty database behavior returns structured empty dictionary."""
        with app.app_context():
            data = load_data_from_db()
            assert data["ec2"] == []
            assert data["ebs"] == []
            assert data["s3"] == []
            assert data["account_cost"] == 0.0
            assert data["summary_metrics"]["total_resources"] == 0

    def test_missing_cost_data_behavior(self, app):
        """9. Test behavior when resources exist but cost data is missing."""
        with app.app_context():
            ResourceRepository.upsert_resource("i-no-cost", "EC2", "ap-south-1", "running")

            data = load_data_from_db()
            assert len(data["ec2"]) == 1
            assert data["ec2"][0]["monthly_cost"] == 0.0
            assert data["account_cost"] == 0.0

    def test_complete_integration_path(self, app):
        """10. Complete integration path from PostgreSQL -> correlation layer -> FinOps analysis."""
        with app.app_context():
            # 1. Store Account cost
            acct = ResourceRepository.upsert_resource("AWS_ACCOUNT", "AWS_ACCOUNT", "global", "active")
            ResourceRepository.upsert_cost_record(acct.id, 150.0)

            # 2. Store EC2 running with low CPU
            ec2 = ResourceRepository.upsert_resource("i-low-cpu", "EC2", "us-east-1", "running")
            ResourceRepository.add_cost_record(ec2.id, 30.0)
            ResourceRepository.upsert_metric(ec2.id, "cpu_utilization", 2.5)

            # 3. Correlation loader
            data = load_data_from_db()

            # 4. Summary & Findings
            summary = generate_summary(data)
            findings = detect_findings(data)
            recs = generate_recommendations(findings)

            assert summary["costs"]["account_cost"] == 150.0
            assert summary["costs"]["ec2"] == 30.0
            assert len(findings) == 1
            assert recs[0].resource_id == "i-low-cpu"
