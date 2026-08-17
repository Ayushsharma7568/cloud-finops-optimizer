# Cloud FinOps + Intelligent Resource Optimization

A cloud cost optimization platform that analyzes cloud resource usage, identifies potential waste, estimates cost savings, and provides structured optimization recommendations.

## Project Status

**Status:** 🚧 In Development — Phase 3 Complete

Phase 3 introduces an intelligent Recommendation Engine that transforms waste findings into clear, explainable, and prioritized actions.

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

## Current Features (Phase 3)

* **Waste Detection Engine**: Identifies underutilized and idle resources.
* **Recommendation Engine**: Transforms technical waste findings into clear, actionable recommendations.
  * Standardized Action Categories (e.g., DOWNSIZE, REVIEW_AND_TERMINATE).
  * Explainable reasoning for each recommendation.
* **Intelligent Scoring**: 
  * **Severity**: Calculates potential cost impact (HIGH, MEDIUM, LOW).
  * **Confidence**: Evaluates certainty of the recommendation based on data availability.
* **Prioritization**: Automatically ranks recommendations by severity and maximum potential savings.
* **Savings Estimator**: Calculates estimated monthly and annual savings using mock pricing assumptions.
* **Dashboard**: Clean UI displaying cost metrics, a top recommendation highlight, and a prioritized action table.
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
  │   ├── data_loader.py            CSV loading and validation
  │   ├── cost_analysis.py          Resource, cost, and utilization analysis
  │   ├── waste_detector.py         Rule-based optimization opportunity detection
  │   ├── recommendation_engine.py  Actionable recommendations and prioritization
  │   └── savings_calculator.py      Savings aggregation and metrics
  └── templates/
      └── index.html       Dashboard template

config.py                  App configuration, thresholds, and mock pricing
run.py                     Application entry point
```

**Data flow:**

```
CSV Files → data_loader → cost_analysis → waste_detector → recommendation_engine → savings_calculator → Route → Template
```

## Technology Stack

* **Backend:** Python, Flask
* **Data:** CSV (mock data)
* **Frontend:** HTML, Vanilla CSS
* **Testing:** pytest (82 tests covering data loading, analysis, waste detection, recommendations, and savings)

## Planned Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Project setup and Flask foundation | ✅ Complete |
| 1 | Mock data, analysis, and metrics dashboard | ✅ Complete |
| 2 | Waste detection, mock savings, optimization summary | ✅ Complete |
| 3 | Recommendation engine, prioritization, and UI | ✅ Complete |
| 4 | AWS API integration (boto3) | 🔜 Planned |
| 5 | Database integration and models | 🔜 Planned |
| 6 | AI-powered optimization recommendations | 🔜 Planned |
| 7 | Advanced dashboard with dynamic charts | 🔜 Planned |

## Important Notes & Limitations

* All data is **mock data**. The application does not currently connect to AWS.
* All pricing and savings estimates are **mock assumptions** for demonstration purposes.
* The application identifies optimization opportunities but does **not** modify or delete any cloud resources.
* Thresholds and mock pricing assumptions are fully configurable in `config.py`.

## Author

**Ayush Sharma**
