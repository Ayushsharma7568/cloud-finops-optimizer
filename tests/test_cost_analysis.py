"""Tests for the cost analysis service."""

import pytest

from app.services.cost_analysis import (
    count_resources_by_type,
    count_resources_by_region,
    count_ec2_by_status,
    calculate_cost_breakdown,
    calculate_ec2_utilization,
    calculate_ebs_utilization,
    detect_underutilized_resources,
    generate_summary,
)
from app.services.data_loader import load_all_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_data():
    """Load the real mock data for integration-style tests."""
    return load_all_data()


@pytest.fixture
def minimal_data():
    """Small hand-crafted dataset for precise unit tests."""
    return {
        "ec2": [
            {
                "resource_id": "i-001", "instance_type": "t3.micro",
                "region": "us-east-1", "status": "running",
                "cpu_utilization": 80.0, "memory_utilization": 70.0,
                "monthly_cost": 10.0,
            },
            {
                "resource_id": "i-002", "instance_type": "m5.large",
                "region": "us-west-2", "status": "stopped",
                "cpu_utilization": 0.0, "memory_utilization": 0.0,
                "monthly_cost": 0.0,
            },
            {
                "resource_id": "i-003", "instance_type": "t3.small",
                "region": "us-east-1", "status": "running",
                "cpu_utilization": 5.0, "memory_utilization": 8.0,
                "monthly_cost": 20.0,
            },
        ],
        "ebs": [
            {
                "volume_id": "vol-001", "volume_type": "gp3",
                "region": "us-east-1", "size_gb": 100.0, "used_gb": 90.0,
                "monthly_cost": 8.0, "status": "in-use",
            },
            {
                "volume_id": "vol-002", "volume_type": "gp3",
                "region": "us-east-1", "size_gb": 500.0, "used_gb": 10.0,
                "monthly_cost": 40.0, "status": "in-use",
            },
        ],
        "s3": [
            {
                "bucket_name": "test-bucket", "region": "us-east-1",
                "storage_gb": 100.0, "monthly_cost": 2.30,
            },
        ],
    }


# ---------------------------------------------------------------------------
# Resource counting
# ---------------------------------------------------------------------------

class TestResourceCounts:
    def test_count_by_type(self, minimal_data):
        counts = count_resources_by_type(minimal_data)
        assert counts == {"ec2": 3, "ebs": 2, "s3": 1}

    def test_count_by_region(self, minimal_data):
        regions = count_resources_by_region(minimal_data)
        assert regions["us-east-1"] == 5
        assert regions["us-west-2"] == 1

    def test_ec2_status_counts(self, minimal_data):
        statuses = count_ec2_by_status(minimal_data["ec2"])
        assert statuses["running"] == 2
        assert statuses["stopped"] == 1


# ---------------------------------------------------------------------------
# Cost calculations
# ---------------------------------------------------------------------------

class TestCostBreakdown:
    def test_total_cost(self, minimal_data):
        costs = calculate_cost_breakdown(minimal_data)
        expected_total = 10.0 + 20.0 + 8.0 + 40.0 + 2.30
        assert costs["total"] == round(expected_total, 2)

    def test_per_service_cost(self, minimal_data):
        costs = calculate_cost_breakdown(minimal_data)
        assert costs["ec2"] == 30.0
        assert costs["ebs"] == 48.0
        assert costs["s3"] == 2.30

    def test_empty_data(self):
        costs = calculate_cost_breakdown({"ec2": [], "ebs": [], "s3": []})
        assert costs["total"] == 0.0

    def test_real_data_costs_positive(self, sample_data):
        costs = calculate_cost_breakdown(sample_data)
        assert costs["total"] > 0
        assert costs["ec2"] > 0
        assert costs["ebs"] > 0
        assert costs["s3"] > 0


# ---------------------------------------------------------------------------
# Utilization
# ---------------------------------------------------------------------------

class TestEC2Utilization:
    def test_average_cpu(self, minimal_data):
        util = calculate_ec2_utilization(minimal_data["ec2"])
        # Running instances: 80.0 and 5.0 → avg = 42.5
        assert util["avg_cpu"] == 42.5

    def test_average_memory(self, minimal_data):
        util = calculate_ec2_utilization(minimal_data["ec2"])
        # Running instances: 70.0 and 8.0 → avg = 39.0
        assert util["avg_memory"] == 39.0

    def test_no_running_instances(self):
        stopped_only = [
            {"status": "stopped", "cpu_utilization": 0.0, "memory_utilization": 0.0}
        ]
        util = calculate_ec2_utilization(stopped_only)
        assert util["avg_cpu"] == 0.0
        assert util["avg_memory"] == 0.0


class TestEBSUtilization:
    def test_total_storage(self, minimal_data):
        util = calculate_ebs_utilization(minimal_data["ebs"])
        assert util["total_allocated_gb"] == 600.0
        assert util["total_used_gb"] == 100.0

    def test_utilization_percentage(self, minimal_data):
        util = calculate_ebs_utilization(minimal_data["ebs"])
        expected_pct = round(100.0 / 600.0 * 100, 1)
        assert util["utilization_pct"] == expected_pct


# ---------------------------------------------------------------------------
# Underutilization detection
# ---------------------------------------------------------------------------

class TestUnderutilizationDetection:
    def test_detects_stopped_ec2(self, minimal_data):
        flags = detect_underutilized_resources(minimal_data)
        stopped = [f for f in flags if "stopped" in f["reason"].lower()]
        assert len(stopped) == 1
        assert stopped[0]["resource_id"] == "i-002"

    def test_detects_low_cpu_ec2(self, minimal_data):
        flags = detect_underutilized_resources(minimal_data)
        low_cpu = [f for f in flags if "cpu" in f["reason"].lower()]
        assert len(low_cpu) == 1
        assert low_cpu[0]["resource_id"] == "i-003"

    def test_detects_underutilized_ebs(self, minimal_data):
        flags = detect_underutilized_resources(minimal_data)
        ebs_flags = [f for f in flags if f["resource_type"] == "EBS"]
        assert len(ebs_flags) == 1
        assert ebs_flags[0]["resource_id"] == "vol-002"

    def test_well_utilized_not_flagged(self, minimal_data):
        flags = detect_underutilized_resources(minimal_data)
        flagged_ids = {f["resource_id"] for f in flags}
        assert "i-001" not in flagged_ids  # 80% CPU is fine
        assert "vol-001" not in flagged_ids  # 90/100 GB is fine

    def test_real_data_returns_flags(self, sample_data):
        flags = detect_underutilized_resources(sample_data)
        assert len(flags) > 0  # mock data has intentional waste


# ---------------------------------------------------------------------------
# Full summary
# ---------------------------------------------------------------------------

class TestGenerateSummary:
    def test_summary_has_all_keys(self, sample_data):
        summary = generate_summary(sample_data)
        assert "resource_counts" in summary
        assert "resources_by_region" in summary
        assert "ec2_status" in summary
        assert "costs" in summary
        assert "ec2_utilization" in summary
        assert "ebs_utilization" in summary
        assert "underutilized_resources" in summary
        assert "total_resources" in summary

    def test_total_resources_matches(self, sample_data):
        summary = generate_summary(sample_data)
        expected = sum(len(v) for v in sample_data.values())
        assert summary["total_resources"] == expected
