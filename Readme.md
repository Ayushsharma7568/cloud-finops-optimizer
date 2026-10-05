# Cloud FinOps + Intelligent Resource Optimization

A cloud cost optimization platform that analyzes cloud resource usage, identifies potential waste, estimates cost savings, and provides structured optimization recommendations.

# Cloud FinOps + Intelligent Resource Optimization

A production-style cloud cost optimization platform that ingests real AWS resources via Boto3 (EC2, EBS, CloudWatch CPU metrics, AWS Cost Explorer), persists infrastructure data into PostgreSQL, correlates multi-dimensional FinOps metrics, detects waste and idle resources, and generates actionable cost reduction recommendations inside a secure, authenticated web platform.

## Project Status

**Status:** ✅ Phase 6 Complete — Production-Ready FinOps Platform

Phase 6 adds secure user authentication, password hashing, session security controls, CSRF protection, protected routes, a modern dark-mode FinOps web dashboard, detailed resource views, interactive analysis execution controls, run auditing, and 180+ automated tests.

---

## Quick Start

### 1. Activate Environment & Run Migrations

```bash
# Activate existing virtual environment (Linux/Ubuntu WSL)
source venv-linux/bin/activate

# Apply database migrations
flask db upgrade
```

### 2. Create Initial Local User

Use the safe CLI command or script to set up your administrator/user account securely:

```bash
# Via Flask CLI
flask create-user

# Or via script
python scripts/create_user.py
```
*You will be prompted to enter a username, email, and password securely.*

### 3. Start the Web Application

```bash
python run.py
```

Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/) to access the login screen.

---

## Run Verification & Tests

```bash
# Run Phase 6 Manual Verification Script
python scripts/verify_phase6.py

# Run Complete Automated Test Suite (181 tests)
pytest
```

---

## Features (Phase 6 Complete)

* **Authentication & Authorization**: `Flask-Login` session management, `Werkzeug` secure password hashing (`pbkdf2:sha256`), protected web routes & 401 API responses.
* **Security Controls**: Double-submit CSRF protection on forms, HTTPOnly & SameSite session cookies, non-committed secret management.
* **AWS & FinOps Pipeline**: Boto3 EC2 & EBS discovery, CloudWatch CPU metrics, AWS Cost Explorer integration without account-level cost duplication.
* **PostgreSQL Infrastructure**: Persistent database models for `Resource`, `ResourceMetric`, `CostRecord`, `AnalysisRun`, `OptimizationFinding`, `Recommendation`, and `User`.
* **FinOps Dashboard**: Dark mode UI with KPI metric cards, Chart.js visual charts, recent analysis history audit trail, and instant `[ Run AWS Analysis ]` execution controls.
* **Resource Inventory & Reporting**: Detailed EC2/EBS views, filterable findings view, prioritized recommendations view, and historical run detail inspection.

---

## Architecture & Documentation

For detailed architectural decisions, security design, and API reference, see:
- [`docs/phase6_production_platform.md`](docs/phase6_production_platform.md)

| 5.3 | AWS Resource Discovery (EC2 + EBS) | ✅ Complete |
| 5.4 | AWS Database Integration | ✅ Complete |
| 5.5 | AWS CloudWatch Metrics Integration | ✅ Complete |
| 5.6 | AWS Cost Explorer Integration | ✅ Complete |
| 5.7 | AWS Resource/Cost Correlation | ✅ Complete |
| 5.8 | Real AWS FinOps Analysis Integration | ✅ Complete |
| 5.9 | FinOps Analysis Runs & Reporting | ✅ Complete |
| 6 | AI-powered optimization recommendations | 🔜 Planned |
| 7 | Advanced dashboard with dynamic charts | 🔜 Planned |

## Important Notes & Limitations

* All data is **mock data**. The application does not currently connect to AWS.
* All pricing and savings estimates are **mock assumptions** for demonstration purposes.
* The application identifies optimization opportunities but does **not** modify or delete any cloud resources.
* Thresholds and mock pricing assumptions are fully configurable in `config.py`.

## Author

**Ayush Sharma**
