import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root directory
BASE_DIR = Path(__file__).resolve().parent


def _get_secret_key() -> str:
    """Retrieve SECRET_KEY from environment, raising an error in production if unconfigured."""
    raw_key = os.getenv("SECRET_KEY", "").strip()
    if raw_key:
        return raw_key

    env_mode = os.getenv("FLASK_ENV", os.getenv("ENV", "development")).lower()
    if env_mode in ["production", "prod"]:
        raise ValueError("CRITICAL: SECRET_KEY must be set in environment for production execution.")

    return "dev-finops-secret-key-change-in-production"


class Config:
    """Base configuration."""

    SECRET_KEY = _get_secret_key()
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session Cookie Security & Protection
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ["true", "1"]
    WTF_CSRF_ENABLED = True

    # AWS Configuration
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")


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
