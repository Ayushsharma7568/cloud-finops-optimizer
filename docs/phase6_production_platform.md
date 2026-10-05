# Phase 6 — Production-Ready FinOps Platform Architecture & Documentation

## Overview

Phase 6 elevates the **Cloud FinOps Optimizer** from a functional backend & correlation engine into a secure, production-grade enterprise web application. It integrates robust user authentication, session security, CSRF protection, protected routes, a modern dark-themed FinOps dashboard, detailed resource inventory views, interactive analysis controls, and auditing capabilities without altering existing database schemas or breaking existing business logic.

---

## Key Architecture & Design System

1. **Backend Framework**: Flask 3.1, Jinja2 template engine, SQLAlchemy 2.0 ORM, Flask-Migrate / Alembic.
2. **Database System**: PostgreSQL 17 running via Docker (`cloud_finops`).
3. **Session & Auth Subsystem**: Flask-Login 0.6.3 + Werkzeug 3.1 secure pbkdf2:sha256 password hashing.
4. **CSRF & Security Layer**: Double-submit cookie CSRF validation token system + HTTPOnly / SameSite session cookies.
5. **UI / Design System**: Pure Vanilla CSS design system with custom CSS variables, dark mode palette, glassmorphism cards, responsive tables, Chart.js visual charts, and status badges.

---

## Authentication & Authorization

- **User Model (`User`)**:
  - `id`: Integer primary key
  - `username`: String(80), unique, indexed
  - `email`: String(120), unique, indexed
  - `password_hash`: String(256)
  - `created_at`: Datetime UTC timestamp
- **Credential Hashing**: Passwords are saved strictly using `Werkzeug` secure salted hash (`generate_password_hash` / `check_password_hash`). Plaintext passwords are never logged or stored.
- **Flask-Login Integration**: Managed via `LoginManager` in `app/__init__.py`. Unauthenticated browser requests redirect automatically to `/login`. Unauthenticated API requests receive HTTP 401 Unauthorized JSON response (`{"error": "Unauthorized"}`).
- **User Creation CLI**:
  - Flask CLI: `flask create-user`
  - Script: `python scripts/create_user.py`
  - Safely creates users via terminal prompts without hardcoded credentials.

---

## Security Hardening & Session Configuration

- **Session Cookies**:
  - `SESSION_COOKIE_HTTPONLY = True`: Prevents client-side JavaScript access to session cookie.
  - `SESSION_COOKIE_SAMESITE = 'Lax'`: Mitigates Cross-Site Request Forgery (CSRF).
  - `SESSION_COOKIE_SECURE = Configurable` (False in local HTTP dev, True in Production HTTPS).
- **CSRF Protection**:
  - Active double-submit token checking (`validate_csrf_token`) on all state-changing HTTP POST routes (`/login`, `/logout`, `/analysis/run`).
  - Jinja template helper `{{ csrf_token() }}` automatically generates and injects tokens into forms.
- **Secret Key Handling**: Secret keys read dynamically from environment variables (`SECRET_KEY`). Default fallback provided only for local development.

---

## FinOps Dashboard & User Interface

1. **Dashboard (`/` or `/dashboard`)**:
   - **Summary KPI Metrics**: Account-level cost ($/mo), potential monthly savings ($/mo), total resources analyzed, waste findings count, recommendations count.
   - **Chart Visualizations**:
     - *Cost & Savings Overview* (bar chart)
     - *Waste Findings by Severity* (doughnut chart)
   - **Analysis Controls**: Direct `[ Run AWS Analysis ]` button triggering full Phase 5.9 analysis pipeline.
   - **Recent Audit Trail**: Quick table of latest 5 analysis runs with status indicators.

2. **Resources View (`/resources`)**:
   - EC2 Instances table: Instance ID, region, status badge, type, CloudWatch CPU utilization bar, resource-level cost (or explicit "Account-level Cost" label).
   - EBS Volumes table: Volume ID, region, status (attached/unattached), size in GB, storage utilization/IOPS, cost.
   - Preserves strict architectural distinction between account-level Cost Explorer data and resource metrics.

3. **Findings View (`/findings`)**:
   - Filterable view of all detected waste findings by **Severity** (CRITICAL, HIGH, MEDIUM, LOW) and **Resource Type** (EC2, EBS, S3).
   - Shows descriptions, issue types, and potential estimated savings.

4. **Recommendations View (`/recommendations`)**:
   - Ranked optimization action cards showing priority badges (P1, P2), action categories (DOWNSIZE, REVIEW_AND_TERMINATE, RESIZE_STORAGE, REVIEW_AND_DELETE), reason, recommendation text, confidence levels, and monthly/annual savings.

5. **Analysis Run History & Detail (`/analysis/history`, `/analysis/<run_id>`)**:
   - History view showing all execution runs, execution timestamps, status badges (`SUCCESS`, `RUNNING`, `FAILED`), and savings totals.
   - Detail page showing specific run summary, error trace if failed, and linked findings & recommendations.

---

## API Endpoints

All REST APIs require authentication:
- `GET /api/analysis/latest`: Formatted summary of the latest successful analysis run.
- `GET /api/analysis/history`: List of recent analysis runs.
- `GET /api/analysis/<run_id>`: Formatted summary of specific run by ID.
- `GET /api/resources`: Raw JSON dictionary of all loaded PostgreSQL resources and metrics.
- `GET /api/findings`: JSON list of all current waste findings.

---

## Manual Verification

Run the comprehensive manual verification script:
```bash
python scripts/verify_phase6.py
```
Output:
```
==================================================
PHASE 6 VERIFICATION
==================================================
Database: OK
Application: OK
Authentication: OK
Protected routes: OK
Dashboard: OK
Analysis history: OK
Resource views: OK
Findings: OK
Recommendations: OK

Tests: PASS

PHASE 6 VERIFICATION: SUCCESS
==================================================
```

---

## Known Limitations & Future Roadmap

1. **Single-Tenant Authentication**: Simple single-role authenticated user model suitable for local/single-team FinOps deployment.
2. **Account-Level Cost Allocation**: Account-level Cost Explorer spend is preserved separately and not artificially split among individual unpriced resources.
3. **Local Dev HTTP**: Session cookies use `SESSION_COOKIE_SECURE=False` during local development; HTTPS reverse proxy recommended in production deployments.
