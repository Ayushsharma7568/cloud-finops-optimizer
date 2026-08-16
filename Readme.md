# Cloud FinOps + Intelligent Resource Optimization

A cloud cost optimization platform that analyzes cloud resource usage, identifies potential waste, estimates cost savings, and provides optimization recommendations.

## Project Status

**Status:** 🚧 In Development — Phase 1 Complete

Phase 1 delivers mock-data analysis with basic FinOps metrics and waste detection.

## Quick Start

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/) to view the dashboard.

## Run Tests

```bash
python -m pytest tests/ -v
```

## Current Features (Phase 1)

* Mock cloud resource data (EC2, EBS, S3)
* CSV-based data loading with validation
* Cost breakdown by service
* EC2 CPU and memory utilization analysis
* EBS storage utilization analysis
* Underutilization and waste detection with configurable thresholds
* Simple web dashboard displaying all metrics

## Architecture

```text
data/                     Mock CSV datasets
  ├── ec2_resources.csv
  ├── ebs_volumes.csv
  └── s3_buckets.csv

app/
  ├── __init__.py          Flask app factory
  ├── routes.py            HTTP route definitions
  ├── models.py            (placeholder — database not yet integrated)
  ├── services/
  │   ├── data_loader.py   CSV loading and validation
  │   └── cost_analysis.py Resource, cost, and utilization analysis
  └── templates/
      └── index.html       Dashboard template

config.py                  App configuration and analysis thresholds
run.py                     Application entry point
```

**Data flow:**

```
CSV Files → data_loader → cost_analysis → Flask route → Template
```

Routes call services; services contain business logic; templates handle presentation.

## Technology Stack

* **Backend:** Python, Flask
* **Data:** CSV (mock data — AWS integration planned)
* **Frontend:** HTML, CSS (minimal dashboard)
* **Testing:** pytest

## Planned Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Project setup and Flask foundation | ✅ Complete |
| 1 | Mock data, analysis, and metrics dashboard | ✅ Complete |
| 2 | Database integration and API endpoints | 🔜 Planned |
| 3 | AWS integration with boto3 | 🔜 Planned |
| 4 | AI-powered optimization recommendations | 🔜 Planned |
| 5 | Advanced dashboard with charts | 🔜 Planned |

## Important Notes

* All current data is **mock/sample data** — not from a real AWS account.
* Analysis thresholds are configurable in `config.py` (`AnalysisThresholds` class).
* Real AWS integration will be implemented in Phase 3.

## Author

**Ayush Sharma**
