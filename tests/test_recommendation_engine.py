"""Tests for the recommendation engine."""

import pytest

from app.services.waste_detector import OptimizationFinding, IssueType, Severity
from app.services.recommendation_engine import (
    generate_recommendations,
    prioritize_recommendations,
    Recommendation,
    ActionCategory,
    Confidence,
    _extract_instance_type,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_findings():
    """Mock findings to test recommendation generation."""
    return [
        OptimizationFinding(
            resource_id="i-underutil", resource_type="EC2",
            issue_type=IssueType.UNDERUTILIZED_EC2, severity=Severity.HIGH,
            reason="Low utilization detected (CPU 5%). Instance type: t3.large.",
            recommended_action="Consider downsizing.",
            current_monthly_cost=60.0,
            estimated_optimized_monthly_cost=30.0,
            estimated_monthly_savings=30.0,
            estimated_annual_savings=360.0,
        ),
        OptimizationFinding(
            resource_id="i-stopped", resource_type="EC2",
            issue_type=IssueType.STOPPED_EC2, severity=Severity.LOW,
            reason="Instance is stopped",
            recommended_action="Review and terminate.",
            current_monthly_cost=0.0,
            estimated_optimized_monthly_cost=0.0,
            estimated_monthly_savings=0.0,
            estimated_annual_savings=0.0,
        ),
        OptimizationFinding(
            resource_id="vol-underutil", resource_type="EBS",
            issue_type=IssueType.UNDERUTILIZED_EBS, severity=Severity.MEDIUM,
            reason="Low storage utilization: 20/500 GB (4%). Volume type: gp3.",
            recommended_action="Consider reducing volume size.",
            current_monthly_cost=40.0,
            estimated_optimized_monthly_cost=20.0,
            estimated_monthly_savings=20.0,
            estimated_annual_savings=240.0,
        ),
        OptimizationFinding(
            resource_id="vol-unattached", resource_type="EBS",
            issue_type=IssueType.UNATTACHED_EBS, severity=Severity.MEDIUM,
            reason="Volume is unattached",
            recommended_action="Review and delete.",
            current_monthly_cost=16.0,
            estimated_optimized_monthly_cost=0.0,
            estimated_monthly_savings=16.0,
            estimated_annual_savings=192.0,
        ),
    ]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_extract_instance_type_success(self):
        reason = "Low utilization detected (CPU 5%). Instance type: t3.large."
        assert _extract_instance_type(reason) == "t3.large"

    def test_extract_instance_type_missing(self):
        reason = "No instance type mentioned here."
        assert _extract_instance_type(reason) == "unknown"


# ---------------------------------------------------------------------------
# Recommendation Generation
# ---------------------------------------------------------------------------

class TestRecommendationGeneration:
    def test_generates_correct_number_of_recommendations(self, sample_findings):
        recs = generate_recommendations(sample_findings)
        assert len(recs) == len(sample_findings)
        
    def test_underutilized_ec2_recommendation(self, sample_findings):
        recs = generate_recommendations(sample_findings)
        rec = next(r for r in recs if r.issue_type == IssueType.UNDERUTILIZED_EC2)
        assert rec.action_category == ActionCategory.DOWNSIZE
        assert rec.confidence == Confidence.MEDIUM
        assert "t3.large" in rec.recommendation
        assert rec.estimated_monthly_savings == 30.0

    def test_stopped_ec2_recommendation(self, sample_findings):
        recs = generate_recommendations(sample_findings)
        rec = next(r for r in recs if r.issue_type == IssueType.STOPPED_EC2)
        assert rec.action_category == ActionCategory.REVIEW_AND_TERMINATE
        assert rec.confidence == Confidence.HIGH

    def test_underutilized_ebs_recommendation(self, sample_findings):
        recs = generate_recommendations(sample_findings)
        rec = next(r for r in recs if r.issue_type == IssueType.UNDERUTILIZED_EBS)
        assert rec.action_category == ActionCategory.RESIZE_STORAGE
        assert rec.confidence == Confidence.MEDIUM

    def test_unattached_ebs_recommendation(self, sample_findings):
        recs = generate_recommendations(sample_findings)
        rec = next(r for r in recs if r.issue_type == IssueType.UNATTACHED_EBS)
        assert rec.action_category == ActionCategory.REVIEW_AND_DELETE
        assert rec.confidence == Confidence.HIGH
        
    def test_unsupported_issue_type_ignored(self):
        unsupported_finding = OptimizationFinding(
            resource_id="s3-bucket", resource_type="S3",
            issue_type="UNKNOWN_ISSUE", severity=Severity.LOW,
            reason="Unknown", recommended_action="None",
            current_monthly_cost=0.0
        )
        recs = generate_recommendations([unsupported_finding])
        assert len(recs) == 0


# ---------------------------------------------------------------------------
# Prioritization
# ---------------------------------------------------------------------------

class TestPrioritization:
    def test_prioritizes_high_over_medium_over_low(self):
        recs = [
            Recommendation(resource_id="low", resource_type="EC2", issue_type=IssueType.STOPPED_EC2, 
                           severity=Severity.LOW, confidence=Confidence.HIGH, reason="", recommendation="", 
                           action_category=ActionCategory.REVIEW_AND_TERMINATE, current_monthly_cost=0),
            Recommendation(resource_id="high", resource_type="EC2", issue_type=IssueType.UNDERUTILIZED_EC2, 
                           severity=Severity.HIGH, confidence=Confidence.MEDIUM, reason="", recommendation="", 
                           action_category=ActionCategory.DOWNSIZE, current_monthly_cost=100),
            Recommendation(resource_id="medium", resource_type="EBS", issue_type=IssueType.UNATTACHED_EBS, 
                           severity=Severity.MEDIUM, confidence=Confidence.HIGH, reason="", recommendation="", 
                           action_category=ActionCategory.REVIEW_AND_DELETE, current_monthly_cost=20),
        ]
        
        prioritized = prioritize_recommendations(recs)
        assert prioritized[0].resource_id == "high"
        assert prioritized[1].resource_id == "medium"
        assert prioritized[2].resource_id == "low"
        
    def test_prioritizes_by_savings_within_severity(self):
        recs = [
            Recommendation(resource_id="med1", resource_type="EBS", issue_type=IssueType.UNATTACHED_EBS, 
                           severity=Severity.MEDIUM, confidence=Confidence.HIGH, reason="", recommendation="", 
                           action_category=ActionCategory.REVIEW_AND_DELETE, current_monthly_cost=20, estimated_monthly_savings=20),
            Recommendation(resource_id="med2", resource_type="EBS", issue_type=IssueType.UNATTACHED_EBS, 
                           severity=Severity.MEDIUM, confidence=Confidence.HIGH, reason="", recommendation="", 
                           action_category=ActionCategory.REVIEW_AND_DELETE, current_monthly_cost=40, estimated_monthly_savings=40),
        ]
        
        prioritized = prioritize_recommendations(recs)
        assert prioritized[0].resource_id == "med2"
        assert prioritized[1].resource_id == "med1"

    def test_empty_list_returns_empty(self):
        assert prioritize_recommendations([]) == []
