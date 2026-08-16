import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root directory
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # Path to mock data directory
    DATA_DIR = BASE_DIR / "data"


class AnalysisThresholds:
    """Configurable thresholds for resource analysis.

    Change these values to adjust sensitivity of underutilization detection.
    """

    # EC2: flag as underutilized if CPU or memory is below this percentage
    EC2_CPU_UNDERUTILIZED = 15.0
    EC2_MEMORY_UNDERUTILIZED = 15.0

    # EBS: flag as underutilized if used_gb / size_gb ratio is below this
    EBS_UTILIZATION_UNDERUTILIZED = 0.20

    # Severity boundaries (monthly cost thresholds in USD)
    HIGH_SEVERITY_COST = 50.0
    MEDIUM_SEVERITY_COST = 15.0
    # Below MEDIUM_SEVERITY_COST → LOW severity


class MockPricing:
    """Mock pricing assumptions for savings estimation.

    These are NOT real AWS prices. They are simplified mock values used
    to demonstrate the optimization analysis flow. Real AWS pricing will
    be integrated in a later phase.

    Downsizing assumes moving to a smaller instance type within the same
    family, which roughly halves the cost.
    """

    # EC2: estimated cost ratio when downsizing (e.g., 0.5 = half the cost)
    EC2_DOWNSIZE_COST_RATIO = 0.50

    # EBS: cost per GB per month (simplified mock rate)
    EBS_COST_PER_GB_MONTH = 0.10

    # EBS: when recommending a right-sized volume, provision this multiplier
    # over the actual used storage (e.g., 1.3 = 30% headroom)
    EBS_RIGHTSIZING_HEADROOM = 1.30
