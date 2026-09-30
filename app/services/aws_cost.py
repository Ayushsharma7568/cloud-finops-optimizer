"""AWS Cost Explorer Integration Service.

Retrieves daily AWS cost data using Boto3 Cost Explorer API ('ce').
Normalizes responses into internal representation with Decimal precision.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError
from app.services.aws_client import (
    AWSClientFactory,
    AWSApiError,
    AWSConnectionError,
    AWSCredentialsError,
)

logger = logging.getLogger(__name__)


class AWSCostService:
    """Service for retrieving cost data from AWS Cost Explorer."""

    def __init__(self, client_factory=None):
        self.client_factory = client_factory or AWSClientFactory()
        try:
            self.client = self.client_factory.get_client("ce")
        except Exception as e:
            logger.error("Failed to initialize Cost Explorer client: %s", e)
            raise AWSConnectionError(f"Failed to initialize Cost Explorer client: {e}")

    def get_daily_costs(
        self, start_date: str = None, end_date: str = None, days: int = 7
    ) -> list[dict]:
        """Retrieve daily unblended costs from AWS Cost Explorer.

        Args:
            start_date (str, optional): Start date string in 'YYYY-MM-DD' format (inclusive).
            end_date (str, optional): End date string in 'YYYY-MM-DD' format (exclusive).
            days (int, optional): Lookback window in days if start_date/end_date are not provided. Defaults to 7.

        Returns:
            list[dict]: Normalized cost records containing start_date, end_date, amount, currency, and estimated.

        Raises:
            ValueError: If date parameters or formats are invalid.
            AWSCredentialsError: If AWS credentials are missing or invalid.
            AWSConnectionError: If endpoint connection fails.
            AWSApiError: If AWS API call fails.
        """
        # Set default dates if not provided
        if not end_date:
            end_dt = datetime.now(timezone.utc).date()
            end_date = end_dt.strftime("%Y-%m-%d")
        else:
            end_dt = self._parse_date(end_date)

        if not start_date:
            start_dt = end_dt - timedelta(days=days)
            start_date = start_dt.strftime("%Y-%m-%d")
        else:
            start_dt = self._parse_date(start_date)

        if start_dt >= end_dt:
            raise ValueError(
                f"start_date ({start_date}) must be earlier than end_date ({end_date})"
            )

        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
            )

            results_by_time = response.get("ResultsByTime", [])
            normalized_records = []

            for period in results_by_time:
                record = self._normalize_period_cost(period)
                if record is not None:
                    normalized_records.append(record)

            return normalized_records

        except NoCredentialsError:
            raise AWSCredentialsError("No AWS credentials found for Cost Explorer.")
        except EndpointConnectionError as e:
            logger.error("Connection error to AWS Cost Explorer: %s", e)
            raise AWSConnectionError(f"Cost Explorer connection error: {e}")
        except ClientError as e:
            logger.error("AWS Cost Explorer API error: %s", e)
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["AccessDeniedException", "AuthFailure", "UnrecognizedClientException"]:
                raise AWSCredentialsError(f"AWS Cost Explorer access error ({error_code}): {e}")
            raise AWSApiError(f"Cost Explorer API error ({error_code}): {e}")
        except Exception as e:
            logger.error("Unexpected error retrieving AWS costs: %s", e)
            raise AWSApiError(f"Unexpected Cost Explorer error: {e}")

    def _normalize_period_cost(self, period: dict) -> dict | None:
        """Parse and normalize a single period item from Cost Explorer API response."""
        time_period = period.get("TimePeriod", {})
        start = time_period.get("Start")
        end = time_period.get("End")

        if not start or not end:
            logger.warning("Skipping Cost Explorer result with missing TimePeriod: %s", period)
            return None

        total = period.get("Total", {})
        unblended = total.get("UnblendedCost", {})

        amount_str = unblended.get("Amount")
        unit = unblended.get("Unit", "USD")
        estimated = period.get("Estimated", False)

        if amount_str is None:
            logger.warning("Missing UnblendedCost Amount for period %s - %s", start, end)
            return None

        try:
            amount_decimal = Decimal(str(amount_str))
        except (InvalidOperation, TypeError, ValueError) as e:
            logger.error("Invalid cost amount format '%s' for period %s - %s: %s", amount_str, start, end, e)
            raise AWSApiError(f"Malformed cost amount '{amount_str}': {e}")

        return {
            "start_date": start,
            "end_date": end,
            "amount": amount_decimal,
            "currency": unit,
            "estimated": bool(estimated),
        }

    @staticmethod
    def _parse_date(date_str: str):
        """Parse string date format YYYY-MM-DD into date object."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format '{date_str}'. Expected 'YYYY-MM-DD'.") from e
