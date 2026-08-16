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
