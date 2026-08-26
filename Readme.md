# Cloud FinOps + Intelligent Resource Optimization

A cloud cost optimization platform that analyzes cloud resource usage, identifies potential waste, estimates cost savings, and provides structured optimization recommendations.

## Project Status

**Status:** 🚧 In Development — Phase 4 Complete

Phase 4 introduces a PostgreSQL persistence layer, allowing findings and analysis runs to be stored safely in a database instead of residing entirely in memory.

## Quick Start

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure Database
# 1. Copy .env.example to .env
# 2. Update DATABASE_URL in .env to point to your PostgreSQL instance
# example: DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/cloud_finops

# Run Database Migrations
flask db upgrade

# Seed Database with Mock CSV Data
python scripts/seed_data.py

# Run the application
python run.py
```

Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/) to view the dashboard.

## Run Tests

```bash
python -m pytest tests/ -v
```

## Current Features (Phase 4)

* **PostgreSQL Database Integration**: Persistent storage of cloud resources, metrics, costs, analysis runs, findings, and recommendations.
* **Database Repositories**: Clean separation between database querying and the core business logic.
* **Waste Detection Engine**: Identifies underutilized and idle resources.
* **Recommendation Engine**: Transforms technical waste findings into clear, actionable recommendations.
* **Dashboard**: Displays real-time database-backed results.

## Architecture

```text
data/                     Mock CSV datasets
scripts/                  
  └── seed_data.py        Import script to migrate CSV to PostgreSQL
app/
  ├── __init__.py         Flask app factory
  ├── models.py           SQLAlchemy database schema definitions
  ├── extensions.py       Database extension configurations
  ├── repositories/       Data Access layer separating DB from services
  ├── routes.py           HTTP route definitions (Orchestrator)
  ├── services/
  │   ├── db_loader.py    Loads repository DB objects to business dictionaries
  │   ├── cost_analysis.py
  │   ├── waste_detector.py
  │   ├── recommendation_engine.py
  │   └── savings_calculator.py
  └── templates/
      └── index.html

config.py                  App configuration, thresholds, and mock pricing
run.py                     Application entry point
```

**Data flow:**

```
PostgreSQL → SQLAlchemy → Repository → db_loader → FinOps Engine (Analysis, Waste, Recommendation) → Repository (Persist findings) → Dashboard Template
```

## Technology Stack

* **Backend:** Python, Flask, SQLAlchemy, Flask-Migrate, psycopg
* **Database:** PostgreSQL
* **Data:** CSV (initial seed mock data)
* **Testing:** pytest (87+ tests covering DB lifecycle, pipeline, and engines)

## Planned Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Project setup and Flask foundation | ✅ Complete |
| 1 | Mock data, analysis, and metrics dashboard | ✅ Complete |
| 2 | Waste detection, mock savings, optimization summary | ✅ Complete |
| 3 | Recommendation engine, prioritization, and UI | ✅ Complete |
| 4 | Database integration and models | ✅ Complete |
| 5 | AWS API integration (boto3) | 🔜 Planned |
| 6 | AI-powered optimization recommendations | 🔜 Planned |
| 7 | Advanced dashboard with dynamic charts | 🔜 Planned |

## Important Notes & Limitations

* All data is **mock data**. The application does not currently connect to AWS.
* All pricing and savings estimates are **mock assumptions** for demonstration purposes.
* The application identifies optimization opportunities but does **not** modify or delete any cloud resources.
* Thresholds and mock pricing assumptions are fully configurable in `config.py`.

## Author

**Ayush Sharma**
