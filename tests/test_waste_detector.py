"""Tests for the waste detection engine."""

import pytest

from app.services.waste_detector import (
    detect_findings,
    IssueType,
    Severity,
    OptimizationFinding,
    _assign_severity,
)
from app.services.data_loader import load_all_data
from config import AnalysisThresholds


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_data():
    """Hand-crafted dataset for precise waste-detection tests."""
    return {
        "ec2": [
            {
                "resource_id": "i-normal", "instance_type": "t3.micro",
                "region": "us-east-1", "status": "running",
                "cpu_utilization": 75.0, "memory_utilization": 60.0,
                "monthly_cost": 10.0,
            },
            {
                "resource_id": "i-underutil", "instance_type": "m5.xlarge",
                "region": "us-east-1", "status": "running",
                "cpu_utilization": 5.0, "memory_utilization": 8.0,
                "monthly_cost": 140.0,
            },
            {
                "resource_id": "i-stopped", "instance_type": "t3.medium",
                "region": "us-east-1", "status": "stopped",
                "cpu_utilization": 0.0, "memory_utilization": 0.0,
                "monthly_cost": 0.0,
            },
        ],
        "ebs": [
            {
                "volume_id": "vol-ok", "volume_type": "gp3",
                "region": "us-east-1", "size_gb": 100.0, "used_gb": 85.0,
                "monthly_cost": 8.0, "status": "in-use",
            },
            {
                "volume_id": "vol-underutil", "volume_type": "gp3",
                "region": "us-east-1", "size_gb": 500.0, "used_gb": 20.0,
                "monthly_cost": 40.0, "status": "in-use",
            },
            {
                "volume_id": "vol-unattached", "volume_type": "gp3",
                "region": "us-east-1", "size_gb": 200.0, "used_gb": 0.0,
                "monthly_cost": 16.0, "status": "available",
            },
        ],
        "s3": [
            {
                "bucket_name": "test-bucket", "region": "us-east-1",
                "storage_gb": 100.0, "monthly_cost": 2.30,
            },
        ],
    }


@pytest.fixture
def sample_data():
    """Load the real mock data for integration-style tests."""
    return load_all_data()


# ---------------------------------------------------------------------------
# EC2 detection
# ---------------------------------------------------------------------------

class TestEC2Detection:
    def test_detects_underutilized_ec2(self, minimal_data):
        findings = detect_findings(minimal_data)
        underutil = [f for f in findings if f.issue_type == IssueType.UNDERUTILIZED_EC2]
        assert len(underutil) == 1
        assert underutil[0].resource_id == "i-underutil"

    def test_detects_stopped_ec2(self, minimal_data):
        findings = detect_findings(minimal_data)
        stopped = [f for f in findings if f.issue_type == IssueType.STOPPED_EC2]
        assert len(stopped) == 1
        assert stopped[0].resource_id == "i-stopped"

    def test_normal_ec2_not_flagged(self, minimal_data):
        findings = detect_findings(minimal_data)
        ids = {f.resource_id for f in findings}
        assert "i-normal" not in ids

    def test_underutilized_ec2_has_savings(self, minimal_data):
        findings = detect_findings(minimal_data)
        underutil = [f for f in findings if f.resource_id == "i-underutil"][0]
        assert underutil.estimated_monthly_savings > 0
        assert underutil.estimated_annual_savings == underutil.estimated_monthly_savings * 12

    def test_underutilized_ec2_optimized_cost_is_half(self, minimal_data):
        findings = detect_findings(minimal_data)
        underutil = [f for f in findings if f.resource_id == "i-underutil"][0]
        assert underutil.estimated_optimized_monthly_cost == 70.0  # 140 * 0.5

    def test_stopped_ec2_savings_equals_cost(self, minimal_data):
        findings = detect_findings(minimal_data)
        stopped = [f for f in findings if f.resource_id == "i-stopped"][0]
        assert stopped.estimated_monthly_savings == stopped.current_monthly_cost


# ---------------------------------------------------------------------------
# EBS detection
# ---------------------------------------------------------------------------

class TestEBSDetection:
    def test_detects_underutilized_ebs(self, minimal_data):
        findings = detect_findings(minimal_data)
        ebs_underutil = [f for f in findings if f.issue_type == IssueType.UNDERUTILIZED_EBS]
        assert len(ebs_underutil) == 1
        assert ebs_underutil[0].resource_id == "vol-underutil"

    def test_detects_unattached_ebs(self, minimal_data):
        findings = detect_findings(minimal_data)
        unattached = [f for f in findings if f.issue_type == IssueType.UNATTACHED_EBS]
        assert len(unattached) == 1
        assert unattached[0].resource_id == "vol-unattached"

    def test_well_utilized_ebs_not_flagged(self, minimal_data):
        findings = detect_findings(minimal_data)
        ids = {f.resource_id for f in findings}
        assert "vol-ok" not in ids

    def test_unattached_ebs_savings_equals_cost(self, minimal_data):
        findings = detect_findings(minimal_data)
        unattached = [f for f in findings if f.resource_id == "vol-unattached"][0]
        assert unattached.estimated_monthly_savings == 16.0

    def test_underutilized_ebs_has_savings(self, minimal_data):
        findings = detect_findings(minimal_data)
        ebs_underutil = [f for f in findings if f.resource_id == "vol-underutil"][0]
        assert ebs_underutil.estimated_monthly_savings > 0


# ---------------------------------------------------------------------------
# S3 detection
# ---------------------------------------------------------------------------

class TestS3Detection:
    def test_no_s3_findings_with_limited_data(self, minimal_data):
        """S3 findings are intentionally omitted due to insufficient mock fields."""
        findings = detect_findings(minimal_data)
        s3_findings = [f for f in findings if f.resource_type == "S3"]
        assert len(s3_findings) == 0


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

class TestSeverity:
    def test_high_severity_for_large_savings(self):
        sev = _assign_severity(100.0, 60.0)
        assert sev == Severity.HIGH

    def test_medium_severity(self):
        sev = _assign_severity(30.0, 20.0)
        assert sev == Severity.MEDIUM

    def test_low_severity_for_small_savings(self):
        sev = _assign_severity(5.0, 5.0)
        assert sev == Severity.LOW

    def test_severity_at_high_boundary(self):
        sev = _assign_severity(50.0, AnalysisThresholds.HIGH_SEVERITY_COST)
        assert sev == Severity.HIGH

    def test_severity_just_below_high(self):
        sev = _assign_severity(49.0, AnalysisThresholds.HIGH_SEVERITY_COST - 0.01)
        assert sev == Severity.MEDIUM

    def test_severity_at_medium_boundary(self):
        sev = _assign_severity(15.0, AnalysisThresholds.MEDIUM_SEVERITY_COST)
        assert sev == Severity.MEDIUM

    def test_severity_just_below_medium(self):
        sev = _assign_severity(14.0, AnalysisThresholds.MEDIUM_SEVERITY_COST - 0.01)
        assert sev == Severity.LOW


# ---------------------------------------------------------------------------
# Findings structure (via to_dict)
# ---------------------------------------------------------------------------

class TestFindingStructure:
    def test_to_dict_has_required_fields(self, minimal_data):
        findings = detect_findings(minimal_data)
        assert len(findings) > 0
        required_keys = {
            "resource_id", "resource_type", "issue_type", "severity",
            "reason", "recommended_action", "current_monthly_cost",
            "estimated_optimized_monthly_cost", "estimated_monthly_savings",
            "estimated_annual_savings",
        }
        for f in findings:
            d = f.to_dict()
            assert required_keys.issubset(d.keys()), f"Missing keys in {d}"

    def test_findings_sorted_by_severity(self, minimal_data):
        findings = detect_findings(minimal_data)
        severity_order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
        for i in range(len(findings) - 1):
            a = severity_order[findings[i].severity]
            b = severity_order[findings[i + 1].severity]
            assert a <= b, "Findings should be sorted HIGH → MEDIUM → LOW"


# ---------------------------------------------------------------------------
# Integration with real mock data
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_real_data_produces_findings(self, sample_data):
        findings = detect_findings(sample_data)
        assert len(findings) > 0

    def test_all_findings_have_valid_issue_types(self, sample_data):
        valid_types = set(IssueType)
        findings = detect_findings(sample_data)
        for f in findings:
            assert f.issue_type in valid_types

    def test_all_findings_have_valid_severity(self, sample_data):
        valid_severities = set(Severity)
        findings = detect_findings(sample_data)
        for f in findings:
            assert f.severity in valid_severities
