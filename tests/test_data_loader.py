"""Tests for the data loading service."""

import pytest

from app.services.data_loader import (
    load_ec2_data,
    load_ebs_data,
    load_s3_data,
    load_all_data,
    DataLoadError,
)
from config import Config


class TestLoadEC2Data:
    """Tests for EC2 data loading."""

    def test_loads_successfully(self):
        data = load_ec2_data()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_expected_resource_count(self):
        data = load_ec2_data()
        assert len(data) == 12

    def test_row_has_required_fields(self):
        data = load_ec2_data()
        row = data[0]
        assert "resource_id" in row
        assert "instance_type" in row
        assert "region" in row
        assert "status" in row
        assert "cpu_utilization" in row
        assert "memory_utilization" in row
        assert "monthly_cost" in row

    def test_numeric_fields_are_floats(self):
        data = load_ec2_data()
        for row in data:
            assert isinstance(row["cpu_utilization"], float)
            assert isinstance(row["memory_utilization"], float)
            assert isinstance(row["monthly_cost"], float)

    def test_contains_running_instances(self):
        data = load_ec2_data()
        running = [r for r in data if r["status"] == "running"]
        assert len(running) > 0

    def test_contains_stopped_instances(self):
        data = load_ec2_data()
        stopped = [r for r in data if r["status"] == "stopped"]
        assert len(stopped) > 0


class TestLoadEBSData:
    """Tests for EBS data loading."""

    def test_loads_successfully(self):
        data = load_ebs_data()
        assert isinstance(data, list)
        assert len(data) == 8

    def test_numeric_fields_are_floats(self):
        data = load_ebs_data()
        for row in data:
            assert isinstance(row["size_gb"], float)
            assert isinstance(row["used_gb"], float)
            assert isinstance(row["monthly_cost"], float)


class TestLoadS3Data:
    """Tests for S3 data loading."""

    def test_loads_successfully(self):
        data = load_s3_data()
        assert isinstance(data, list)
        assert len(data) == 6

    def test_numeric_fields_are_floats(self):
        data = load_s3_data()
        for row in data:
            assert isinstance(row["storage_gb"], float)
            assert isinstance(row["monthly_cost"], float)


class TestLoadAllData:
    """Tests for loading all datasets together."""

    def test_returns_all_three_services(self):
        data = load_all_data()
        assert "ec2" in data
        assert "ebs" in data
        assert "s3" in data

    def test_each_service_has_data(self):
        data = load_all_data()
        for service, resources in data.items():
            assert len(resources) > 0, f"{service} should have data"


class TestErrorHandling:
    """Tests for data loading error handling."""

    def test_missing_file_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "DATA_DIR", tmp_path)
        with pytest.raises(DataLoadError, match="not found"):
            load_ec2_data()

    def test_empty_file_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "DATA_DIR", tmp_path)
        (tmp_path / "ec2_resources.csv").write_text("")
        with pytest.raises(DataLoadError, match="empty"):
            load_ec2_data()

    def test_missing_columns_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "DATA_DIR", tmp_path)
        (tmp_path / "ec2_resources.csv").write_text("resource_id,instance_type\ni-001,t3.micro\n")
        with pytest.raises(DataLoadError, match="Missing columns"):
            load_ec2_data()

    def test_invalid_numeric_value_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "DATA_DIR", tmp_path)
        header = "resource_id,instance_type,region,status,cpu_utilization,memory_utilization,monthly_cost"
        row = "i-001,t3.micro,us-east-1,running,NOT_A_NUMBER,50.0,8.50"
        (tmp_path / "ec2_resources.csv").write_text(f"{header}\n{row}\n")
        with pytest.raises(DataLoadError, match="Invalid numeric value"):
            load_ec2_data()
