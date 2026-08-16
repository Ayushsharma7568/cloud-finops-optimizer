"""Service for loading mock cloud resource data from CSV files."""

import csv

from config import Config


# Expected columns for each resource type
EXPECTED_COLUMNS = {
    "ec2": [
        "resource_id", "instance_type", "region", "status",
        "cpu_utilization", "memory_utilization", "monthly_cost",
    ],
    "ebs": [
        "volume_id", "volume_type", "region", "size_gb",
        "used_gb", "monthly_cost", "status",
    ],
    "s3": [
        "bucket_name", "region", "storage_gb", "monthly_cost",
    ],
}

# Fields that must be parsed as floats
FLOAT_FIELDS = {
    "cpu_utilization", "memory_utilization", "monthly_cost",
    "size_gb", "used_gb", "storage_gb",
}


class DataLoadError(Exception):
    """Raised when data loading fails."""


def _parse_row(row: dict, resource_type: str) -> dict:
    """Parse a CSV row, converting numeric fields to floats.

    Args:
        row: Raw CSV row as an ordered dict of strings.
        resource_type: One of 'ec2', 'ebs', 's3'.

    Returns:
        Parsed row dict with numeric fields converted.

    Raises:
        DataLoadError: If a numeric field cannot be parsed.
    """
    parsed = {}
    for key, value in row.items():
        key = key.strip()
        value = value.strip()
        if key in FLOAT_FIELDS:
            try:
                parsed[key] = float(value)
            except (ValueError, TypeError):
                raise DataLoadError(
                    f"Invalid numeric value '{value}' for field '{key}' "
                    f"in {resource_type} data"
                )
        else:
            parsed[key] = value
    return parsed


def _validate_columns(headers: list[str], resource_type: str) -> None:
    """Check that all expected columns are present in the CSV headers.

    Raises:
        DataLoadError: If any required column is missing.
    """
    expected = set(EXPECTED_COLUMNS[resource_type])
    actual = {h.strip() for h in headers}
    missing = expected - actual
    if missing:
        raise DataLoadError(
            f"Missing columns in {resource_type} data: {sorted(missing)}"
        )


def _load_csv(filename: str, resource_type: str) -> list[dict]:
    """Load and validate a single CSV file.

    Args:
        filename: Name of the CSV file inside the data directory.
        resource_type: One of 'ec2', 'ebs', 's3'.

    Returns:
        List of parsed row dicts.

    Raises:
        DataLoadError: If the file is missing, empty, or malformed.
    """
    filepath = Config.DATA_DIR / filename
    if not filepath.exists():
        raise DataLoadError(f"Data file not found: {filepath}")

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise DataLoadError(f"Data file is empty: {filepath}")

        _validate_columns(reader.fieldnames, resource_type)

        rows = []
        for i, row in enumerate(reader, start=2):  # line 1 is the header
            try:
                rows.append(_parse_row(row, resource_type))
            except DataLoadError as e:
                raise DataLoadError(f"Row {i} in {filename}: {e}") from e

    return rows


def load_ec2_data() -> list[dict]:
    """Load EC2 instance data."""
    return _load_csv("ec2_resources.csv", "ec2")


def load_ebs_data() -> list[dict]:
    """Load EBS volume data."""
    return _load_csv("ebs_volumes.csv", "ebs")


def load_s3_data() -> list[dict]:
    """Load S3 bucket data."""
    return _load_csv("s3_buckets.csv", "s3")


def load_all_data() -> dict[str, list[dict]]:
    """Load all mock cloud resource datasets.

    Returns:
        Dict with keys 'ec2', 'ebs', 's3' mapping to lists of resource dicts.

    Raises:
        DataLoadError: If any dataset fails to load.
    """
    return {
        "ec2": load_ec2_data(),
        "ebs": load_ebs_data(),
        "s3": load_s3_data(),
    }
