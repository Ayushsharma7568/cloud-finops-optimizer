# Cloud FinOps + Intelligent Resource Optimization

A cloud cost optimization platform that analyzes cloud resource usage, identifies potential waste, estimates cost savings, and provides structured optimization recommendations.

## Project Status

**Status:** 🚧 In Development — Phase 2 Complete

Phase 2 builds upon the initial architecture to provide an intelligent Waste Detection Engine and Mock Savings Estimator.

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

## Current Features (Phase 2)

* **Waste Detection Engine**: Identifies underutilized and idle resources.
  * EC2: Underutilized CPU/Memory, Stopped instances.
  * EBS: Underutilized storage, Unattached volumes.
* **Intelligent Severity**: Automatically categorizes findings into HIGH, MEDIUM, or LOW severity based on potential cost impact.
* **Savings Estimator**: Calculates estimated monthly and annual savings using mock pricing assumptions.
* **Optimization Summary**: Aggregates total potential savings, opportunity counts, and savings percentage.
* **Dashboard**: Clean UI displaying both the core cost metrics (Phase 1) and actionable optimization recommendations (Phase 2).
* **Mock Datasets**: Realistic mock cloud resource data (EC2, EBS, S3) loaded from CSV.

## Architecture

```text
data/                     Mock CSV datasets
  ├── ec2_resources.csv
  ├── ebs_volumes.csv
  └── s3_buckets.csv

app/
  ├── __init__.py          Flask app factory
  ├── routes.py            HTTP route definitions (Orchestrator)
  ├── services/
  │   ├── data_loader.py       CSV loading and validation
  │   ├── cost_analysis.py     Resource, cost, and utilization analysis
  │   ├── waste_detector.py    Rule-based optimization opportunity detection
  │   └── savings_calculator.py Savings aggregation and metrics
  └── templates/
      └── index.html       Dashboard template

config.py                  App configuration, thresholds, and mock pricing
run.py                     Application entry point
```

**Data flow:**

```
CSV Files → data_loader → cost_analysis → waste_detector → savings_calculator → Route → Template
```

## Technology Stack

* **Backend:** Python, Flask
* **Data:** CSV (mock data)
* **Frontend:** HTML, Vanilla CSS
* **Testing:** pytest (71 tests covering data loading, analysis, waste detection, and savings)

## Planned Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Project setup and Flask foundation | ✅ Complete |
| 1 | Mock data, analysis, and metrics dashboard | ✅ Complete |
| 2 | Waste detection, mock savings, optimization summary | ✅ Complete |
| 3 | AWS API integration (boto3) | 🔜 Planned |
| 4 | Database integration and models | 🔜 Planned |
| 5 | AI-powered optimization recommendations | 🔜 Planned |
| 6 | Advanced dashboard with dynamic charts | 🔜 Planned |

## Important Notes & Limitations

* All data is **mock data**. The application does not currently connect to AWS.
* All pricing and savings estimates are **mock assumptions** for demonstration purposes.
* The application identifies optimization opportunities but does **not** modify or delete any cloud resources.
* Thresholds and mock pricing assumptions are fully configurable in `config.py`.

## Author

**Ayush Sharma**
