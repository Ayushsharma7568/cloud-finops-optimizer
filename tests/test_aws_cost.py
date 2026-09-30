"""Tests for AWS Cost Explorer integration and persistence."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError

from app import create_app
from app.extensions import db
from app.models import CostRecord, Resource
from app.repositories.resource_repository import ResourceRepository
from app.services.aws_client import (
    AWSApiError,
    AWSConnectionError,
    AWSCredentialsError,
)
from app.services.aws_cost import AWSCostService
from app.services.aws_ingestion import sync_aws_costs


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


class TestAWSCostService:

    @patch("app.services.aws_cost.AWSClientFactory")
    def test_client_creation_success(self, mock_factory_cls):
        """Test successful Cost Explorer client creation."""
        mock_factory = MagicMock()
        mock_ce_client = MagicMock()
        mock_factory.get_client.return_value = mock_ce_client
        mock_factory_cls.return_value = mock_factory

        service = AWSCostService()
        mock_factory.get_client.assert_called_once_with("ce")
        assert service.client == mock_ce_client

    @patch("app.services.aws_cost.AWSClientFactory")
    def test_client_creation_failure(self, mock_factory_cls):
        """Test handling of client creation failure."""
        mock_factory = MagicMock()
        mock_factory.get_client.side_effect = Exception("Factory failed")
        mock_factory_cls.return_value = mock_factory

        with pytest.raises(AWSConnectionError, match="Failed to initialize Cost Explorer client"):
            AWSCostService()

    def test_get_daily_costs_parsing_success(self):
        """Test parsing of ResultsByTime, TimePeriod, UnblendedCost, Amount, Unit, Estimated."""
        mock_factory = MagicMock()
        mock_ce_client = MagicMock()
        mock_factory.get_client.return_value = mock_ce_client

        mock_ce_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-09-23", "End": "2026-09-24"},
                    "Total": {
                        "UnblendedCost": {
                            "Amount": "0.0000000074",
                            "Unit": "USD",
                        }
                    },
                    "Estimated": True,
                },
                {
                    "TimePeriod": {"Start": "2026-09-24", "End": "2026-09-25"},
                    "Total": {
                        "UnblendedCost": {
                            "Amount": "1.2345000000",
                            "Unit": "USD",
                        }
                    },
                    "Estimated": False,
                },
            ]
        }

        service = AWSCostService(client_factory=mock_factory)
        records = service.get_daily_costs(start_date="2026-09-23", end_date="2026-09-25")

        assert len(records) == 2
        assert records[0]["start_date"] == "2026-09-23"
        assert records[0]["end_date"] == "2026-09-24"
        assert records[0]["amount"] == Decimal("0.0000000074")
        assert records[0]["currency"] == "USD"
        assert records[0]["estimated"] is True

        assert records[1]["start_date"] == "2026-09-24"
        assert records[1]["amount"] == Decimal("1.2345000000")
        assert records[1]["estimated"] is False

    def test_decimal_money_handling(self):
        """Test that monetary values are returned as Decimal with high precision."""
        mock_factory = MagicMock()
        mock_ce_client = MagicMock()
        mock_factory.get_client.return_value = mock_ce_client

        mock_ce_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-09-23", "End": "2026-09-24"},
                    "Total": {"UnblendedCost": {"Amount": "100.0000000005", "Unit": "USD"}},
                    "Estimated": False,
                }
            ]
        }

        service = AWSCostService(client_factory=mock_factory)
        records = service.get_daily_costs(start_date="2026-09-23", end_date="2026-09-24")

        assert isinstance(records[0]["amount"], Decimal)
        assert records[0]["amount"] == Decimal("100.0000000005")

    def test_empty_results_by_time(self):
        """Test handling when ResultsByTime is empty."""
        mock_factory = MagicMock()
        mock_ce_client = MagicMock()
        mock_factory.get_client.return_value = mock_ce_client

        mock_ce_client.get_cost_and_usage.return_value = {"ResultsByTime": []}

        service = AWSCostService(client_factory=mock_factory)
        records = service.get_daily_costs(start_date="2026-09-23", end_date="2026-09-24")

        assert records == []

    def test_missing_cost_data(self):
        """Test handling of periods with missing cost or amount data."""
        mock_factory = MagicMock()
        mock_ce_client = MagicMock()
        mock_factory.get_client.return_value = mock_ce_client

        mock_ce_client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-09-23", "End": "2026-09-24"},
                    "Total": {},  # missing UnblendedCost
                },
                {
                    "TimePeriod": {},  # missing Start/End
                    "Total": {"UnblendedCost": {"Amount": "1.0", "Unit": "USD"}},
                },
            ]
        }

        service = AWSCostService(client_factory=mock_factory)
        records = service.get_daily_costs(start_date="2026-09-23", end_date="2026-09-24")

        # Incomplete records are safely skipped
        assert records == []

    def test_aws_client_error_handling(self):
        """Test handling of AWS ClientError and connection errors."""
        mock_factory = MagicMock()
        mock_ce_client = MagicMock()
        mock_factory.get_client.return_value = mock_ce_client

        # ClientError
        error_response = {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}}
        mock_ce_client.get_cost_and_usage.side_effect = ClientError(error_response, "GetCostAndUsage")

        service = AWSCostService(client_factory=mock_factory)
        with pytest.raises(AWSCredentialsError, match="AWS Cost Explorer access error"):
            service.get_daily_costs(start_date="2026-09-23", end_date="2026-09-24")

        # EndpointConnectionError
        mock_ce_client.get_cost_and_usage.side_effect = EndpointConnectionError(endpoint_url="http://ce")
        with pytest.raises(AWSConnectionError, match="Cost Explorer connection error"):
            service.get_daily_costs(start_date="2026-09-23", end_date="2026-09-24")

        # NoCredentialsError
        mock_ce_client.get_cost_and_usage.side_effect = NoCredentialsError()
        with pytest.raises(AWSCredentialsError, match="No AWS credentials found"):
            service.get_daily_costs(start_date="2026-09-23", end_date="2026-09-24")

    def test_invalid_date_range_handling(self):
        """Test validation of start_date and end_date."""
        service = AWSCostService(client_factory=MagicMock())

        # Invalid format
        with pytest.raises(ValueError, match="Invalid date format"):
            service.get_daily_costs(start_date="2026/09/23", end_date="2026-09-24")

        # Start date >= End date
        with pytest.raises(ValueError, match="start_date .* must be earlier than end_date"):
            service.get_daily_costs(start_date="2026-09-25", end_date="2026-09-24")


class TestCostRepositoryPersistence:

    def test_upsert_cost_record_persistence(self, app):
        """Test upserting cost records into database."""
        with app.app_context():
            res = ResourceRepository.upsert_resource("AWS_ACCOUNT", "AWS_ACCOUNT", "global", "active")
            rec_dt = datetime(2026, 9, 23, 0, 0, 0)

            # Insert
            cost1 = ResourceRepository.upsert_cost_record(res.id, 15.50, recorded_at=rec_dt)
            assert cost1.id is not None
            assert cost1.monthly_cost == 15.50
            assert cost1.recorded_at == rec_dt

            # Update same date
            cost2 = ResourceRepository.upsert_cost_record(res.id, 20.75, recorded_at=rec_dt)
            assert cost2.id == cost1.id
            assert cost2.monthly_cost == 20.75

            # Verify total DB records
            all_costs = CostRecord.query.filter_by(resource_id=res.id).all()
            assert len(all_costs) == 1
            assert all_costs[0].monthly_cost == 20.75

    @patch("app.services.aws_ingestion.AWSCostService")
    def test_sync_aws_costs_integration_and_idempotency(self, mock_cost_service_cls, app):
        """Test sync_aws_costs integration and idempotency across multiple runs."""
        with app.app_context():
            mock_cost_service = MagicMock()
            mock_cost_service_cls.return_value = mock_cost_service

            mock_cost_service.get_daily_costs.return_value = [
                {
                    "start_date": "2026-09-23",
                    "end_date": "2026-09-24",
                    "amount": Decimal("10.50"),
                    "currency": "USD",
                    "estimated": False,
                },
                {
                    "start_date": "2026-09-24",
                    "end_date": "2026-09-25",
                    "amount": Decimal("12.00"),
                    "currency": "USD",
                    "estimated": False,
                },
            ]

            # First sync
            records1 = sync_aws_costs(start_date="2026-09-23", end_date="2026-09-25")
            assert len(records1) == 2

            account_res = Resource.query.filter_by(resource_id="AWS_ACCOUNT").first()
            assert account_res is not None

            costs_in_db = CostRecord.query.filter_by(resource_id=account_res.id).all()
            assert len(costs_in_db) == 2

            # Second sync with updated value for second day
            mock_cost_service.get_daily_costs.return_value = [
                {
                    "start_date": "2026-09-23",
                    "end_date": "2026-09-24",
                    "amount": Decimal("10.50"),
                    "currency": "USD",
                    "estimated": False,
                },
                {
                    "start_date": "2026-09-24",
                    "end_date": "2026-09-25",
                    "amount": Decimal("14.50"),  # updated amount
                    "currency": "USD",
                    "estimated": False,
                },
            ]

            records2 = sync_aws_costs(start_date="2026-09-23", end_date="2026-09-25")
            assert len(records2) == 2

            # Ensure total count in DB remains 2 (idempotent)
            costs_in_db_after = CostRecord.query.filter_by(resource_id=account_res.id).all()
            assert len(costs_in_db_after) == 2

            day2_cost = CostRecord.query.filter_by(
                resource_id=account_res.id, recorded_at=datetime(2026, 9, 24, 0, 0, 0)
            ).first()
            assert day2_cost.monthly_cost == 14.50
