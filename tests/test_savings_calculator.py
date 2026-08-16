"""Tests for the savings calculator service."""

import pytest

from app.services.waste_detector import (
    detect_findings,
    OptimizationFinding,
    IssueType,
    Severity,
)
from app.services.savings_calculator import (
    calculate_savings_by_service,
    generate_optimization_summary,
)
from app.services.data_loader import load_all_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_findings():
    """Hand-crafted findings for precise savings tests."""
    return [
        OptimizationFinding(
            resource_id="i-001", resource_type="EC2",
            issue_type=IssueType.UNDERUTILIZED_EC2, severity=Severity.HIGH,
            reason="Low CPU", recommended_action="Downsize",
            current_monthly_cost=60.0,
            estimated_optimized_monthly_cost=30.0,
            estimated_monthly_savings=30.0,
            estimated_annual_savings=360.0,
        ),
        OptimizationFinding(
            resource_id="vol-001", resource_type="EBS",
            issue_type=IssueType.UNATTACHED_EBS, severity=Severity.MEDIUM,
            reason="Unattached", recommended_action="Review and delete",
            current_monthly_cost=16.0,
            estimated_optimized_monthly_cost=0.0,
            estimated_monthly_savings=16.0,
            estimated_annual_savings=192.0,
        ),
        OptimizationFinding(
            resource_id="i-002", resource_type="EC2",
            issue_type=IssueType.STOPPED_EC2, severity=Severity.LOW,
            reason="Stopped", recommended_action="Terminate if unused",
            current_monthly_cost=0.0,
            estimated_optimized_monthly_cost=0.0,
            estimated_monthly_savings=0.0,
            estimated_annual_savings=0.0,
        ),
    ]


# ---------------------------------------------------------------------------
# Savings by service
# ---------------------------------------------------------------------------

class TestSavingsByService:
    def test_groups_by_service(self, sample_findings):
        by_service = calculate_savings_by_service(sample_findings)
        assert by_service["EC2"] == 30.0
        assert by_service["EBS"] == 16.0

    def test_empty_findings(self):
        by_service = calculate_savings_by_service([])
        assert by_service == {}


# ---------------------------------------------------------------------------
# Optimization summary
# ---------------------------------------------------------------------------

class TestOptimizationSummary:
    def test_total_monthly_savings(self, sample_findings):
        summary = generate_optimization_summary(sample_findings, 200.0)
        assert summary["total_monthly_savings"] == 46.0

    def test_total_annual_savings(self, sample_findings):
        summary = generate_optimization_summary(sample_findings, 200.0)
        assert summary["total_annual_savings"] == 552.0

    def test_savings_percentage(self, sample_findings):
        summary = generate_optimization_summary(sample_findings, 200.0)
        expected_pct = round(46.0 / 200.0 * 100, 1)
        assert summary["savings_percentage"] == expected_pct

    def test_savings_percentage_zero_cost(self, sample_findings):
        summary = generate_optimization_summary(sample_findings, 0.0)
        assert summary["savings_percentage"] == 0.0

    def test_total_opportunities(self, sample_findings):
        summary = generate_optimization_summary(sample_findings, 200.0)
        assert summary["total_opportunities"] == 3

    def test_high_severity_count(self, sample_findings):
        summary = generate_optimization_summary(sample_findings, 200.0)
        assert summary["high_severity_count"] == 1

    def test_findings_included_as_dicts(self, sample_findings):
        summary = generate_optimization_summary(sample_findings, 200.0)
        assert len(summary["findings"]) == 3
        assert isinstance(summary["findings"][0], dict)

    def test_zero_savings(self):
        findings = [
            OptimizationFinding(
                resource_id="i-zero", resource_type="EC2",
                issue_type=IssueType.STOPPED_EC2, severity=Severity.LOW,
                reason="Stopped", recommended_action="Review",
                current_monthly_cost=0.0,
                estimated_monthly_savings=0.0,
                estimated_annual_savings=0.0,
            ),
        ]
        summary = generate_optimization_summary(findings, 100.0)
        assert summary["total_monthly_savings"] == 0.0
        assert summary["total_annual_savings"] == 0.0
        assert summary["savings_percentage"] == 0.0

    def test_empty_findings(self):
        summary = generate_optimization_summary([], 100.0)
        assert summary["total_monthly_savings"] == 0.0
        assert summary["total_opportunities"] == 0
        assert summary["high_severity_count"] == 0
        assert summary["savings_by_service"] == {}


# ---------------------------------------------------------------------------
# Integration with real mock data
# ---------------------------------------------------------------------------

class TestSavingsIntegration:
    def test_real_data_summary(self):
        data = load_all_data()
        from app.services.cost_analysis import calculate_cost_breakdown
        costs = calculate_cost_breakdown(data)
        findings_objs = detect_findings.__wrapped__(data) if hasattr(detect_findings, '__wrapped__') else None

        # Use the public API which returns dicts via to_dict()
        # We need the OptimizationFinding objects for the calculator
        from app.services.waste_detector import _detect_ec2_findings, _detect_ebs_findings
        finding_objs = _detect_ec2_findings(data["ec2"]) + _detect_ebs_findings(data["ebs"])

        summary = generate_optimization_summary(finding_objs, costs["total"])

        assert summary["total_monthly_savings"] > 0
        assert summary["total_annual_savings"] > 0
        assert summary["total_opportunities"] > 0
        assert summary["savings_percentage"] > 0
