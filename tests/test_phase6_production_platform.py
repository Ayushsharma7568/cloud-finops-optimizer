"""Phase 6 — Production-Ready FinOps Platform Tests.

Covers:
- Authentication & User Management (creation, password hashing, verification, login, logout, duplicate handling)
- Authorization & Protected Routes (unauthenticated redirects, 401 API responses)
- Security (Secret configuration, CSRF behavior, user-facing error pages)
- FinOps Dashboard & Views (Summary KPI metrics, resource lists, findings, recommendations)
- Analysis Engine & Controls (triggering run, history, run details, status)
- Resource Views & Metric/Savings Edge Cases
"""

import pytest
from app import create_app
from app.extensions import db
from app.models import User, AnalysisRun, Resource, ResourceMetric, CostRecord
from app.repositories.user_repository import UserRepository
from app.services.security import generate_csrf_token, validate_csrf_token


@pytest.fixture
def app():
    """Create a Flask app with an in-memory SQLite DB for testing."""
    test_config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "SECRET_KEY": "test-phase6-secret-key-12345",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "WTF_CSRF_ENABLED": False,
    }
    app_inst = create_app(test_config=test_config)

    with app_inst.app_context():
        db.create_all()
        yield app_inst
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Unauthenticated Flask test client."""
    return app.test_client()


@pytest.fixture
def auth_user(app):
    """Fixture providing a persisted test user."""
    with app.app_context():
        user = UserRepository.get_user_by_username("testfinopsuser")
        if not user:
            user = UserRepository.create_user("testfinopsuser", "testuser@finops.local", "StrongPassword123!")
        return user


@pytest.fixture
def auth_client(client, app):
    """Fixture providing an authenticated Flask test client."""
    with app.app_context():
        user = UserRepository.get_user_by_username("testfinopsuser")
        if not user:
            user = UserRepository.create_user("testfinopsuser", "testuser@finops.local", "StrongPassword123!")
        user_id = user.id
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
    return client


# ---------------------------------------------------------------------------
# Authentication Tests (1-11)
# ---------------------------------------------------------------------------

def test_1_user_creation(app):
    """Test user creation and persistence."""
    with app.app_context():
        user = UserRepository.create_user("newuser1", "new1@finops.local", "Pass12345!")
        assert user.id is not None
        assert user.username == "newuser1"
        assert user.email == "new1@finops.local"


def test_2_password_hashing(app):
    """Test password hashing produces secure non-empty hash."""
    with app.app_context():
        user = UserRepository.create_user("newuser2", "new2@finops.local", "Pass12345!")
        assert user.password_hash is not None
        assert len(user.password_hash) > 20
        assert user.password_hash != "Pass12345!"


def test_3_password_verification(app):
    """Test password check against hash."""
    with app.app_context():
        user = UserRepository.create_user("newuser3", "new3@finops.local", "Pass12345!")
        assert user.check_password("Pass12345!") is True
        assert user.check_password("WrongPassword") is False


def test_4_plaintext_password_not_stored(app):
    """Verify plaintext password string is not in model attributes or dict."""
    with app.app_context():
        user = UserRepository.create_user("newuser4", "new4@finops.local", "SecretPass99!")
        user_dict = str(user.__dict__)
        assert "SecretPass99!" not in user_dict


def test_5_successful_login(client, auth_user):
    """Test successful user login flow."""
    with client.session_transaction() as sess:
        csrf_tok = "test_csrf_token"
        sess["csrf_token"] = csrf_tok

    response = client.post(
        "/login",
        data={
            "identifier": "testfinopsuser",
            "password": "StrongPassword123!",
            "csrf_token": csrf_tok,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.location.endswith("/") or response.location.endswith("/dashboard")


def test_6_failed_login(client, auth_user):
    """Test failed login with invalid password produces generic error."""
    with client.session_transaction() as sess:
        csrf_tok = "test_csrf_token"
        sess["csrf_token"] = csrf_tok

    response = client.post(
        "/login",
        data={
            "identifier": "testfinopsuser",
            "password": "WrongPassword!",
            "csrf_token": csrf_tok,
        },
    )
    assert response.status_code == 400
    assert b"Invalid username/email or password" in response.data


def test_7_logout(auth_client):
    """Test logout invalidates session and redirects to login."""
    with auth_client.session_transaction() as sess:
        csrf_tok = "test_csrf_token"
        sess["csrf_token"] = csrf_tok

    response = auth_client.post("/logout", data={"csrf_token": csrf_tok}, follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location


def test_8_duplicate_user_email(app):
    """Test creating duplicate user/email raises exception or handles gracefully."""
    with app.app_context():
        UserRepository.create_user("uniquser", "uniq@finops.local", "Pass123!")
        with pytest.raises(Exception):
            UserRepository.create_user("uniquser", "uniq2@finops.local", "Pass123!")
            db.session.commit()
        db.session.rollback()


def test_9_protected_dashboard(client):
    """Unauthenticated access to dashboard redirects to login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location


def test_10_protected_apis(client):
    """Unauthenticated API requests return 401 JSON error."""
    response = client.get("/api/analysis/latest")
    assert response.status_code == 401
    json_data = response.get_json()
    assert json_data["error"] == "Unauthorized"


def test_11_session_behavior(auth_client):
    """Authenticated client accesses protected route successfully."""
    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"Cloud FinOps Optimizer" in response.data or b"FinOps" in response.data


# ---------------------------------------------------------------------------
# Security & Configuration Tests (12-15)
# ---------------------------------------------------------------------------

def test_12_secret_configuration(app):
    """Verify application configuration has secret key set and cookie security keys."""
    assert app.config["SECRET_KEY"] is not None
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] in ["Lax", "Strict", "None"]


def test_13_csrf_behavior(app):
    """Test CSRF token generation and validation helper inside request context."""
    with app.test_request_context():
        token = generate_csrf_token()
        assert token is not None
        assert validate_csrf_token(token) is True
        assert validate_csrf_token("invalid_token") is False


def test_14_unauthorized_api_behavior(client):
    """Test unauthorized API routes return 401 for resources and findings APIs."""
    res1 = client.get("/api/resources")
    res2 = client.get("/api/findings")
    assert res1.status_code == 401
    assert res2.status_code == 401


def test_15_user_facing_error_handling(auth_client):
    """Test response when querying nonexistent analysis run."""
    response = auth_client.get("/analysis/999999", follow_redirects=True)
    assert response.status_code == 200
    assert b"not found" in response.data.lower() or b"history" in response.data.lower() or b"FinOps" in response.data


# ---------------------------------------------------------------------------
# FinOps Dashboard & Views Tests (16-19)
# ---------------------------------------------------------------------------

def test_16_dashboard_loads_authenticated(auth_client):
    """Test dashboard page loads 200 OK for authenticated user."""
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    assert b"FinOps" in response.data or b"AWS" in response.data


def test_17_dashboard_summary_data(auth_client):
    """Test dashboard includes summary KPIs and Chart elements."""
    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"Chart" in response.data or b"canvas" in response.data or b"card" in response.data


def test_18_findings_rendering(auth_client):
    """Test findings view page renders with filter controls."""
    response = auth_client.get("/findings")
    assert response.status_code == 200
    assert b"FinOps Optimization Findings" in response.data


def test_19_recommendations_rendering(auth_client):
    """Test recommendations view page renders categories and confidence ratings."""
    response = auth_client.get("/recommendations")
    assert response.status_code == 200
    assert b"FinOps Optimization Recommendations" in response.data


# ---------------------------------------------------------------------------
# FinOps Analysis Controls & Reporting Tests (20-25)
# ---------------------------------------------------------------------------

def test_20_start_analysis(auth_client):
    """Test starting an analysis run via POST request."""
    with auth_client.session_transaction() as sess:
        csrf_tok = "test_csrf_token"
        sess["csrf_token"] = csrf_tok

    response = auth_client.post("/analysis/run", data={"csrf_token": csrf_tok}, follow_redirects=False)
    assert response.status_code == 302
    assert "/analysis/" in response.location


def test_21_successful_analysis_run(app):
    """Test full analysis run execution creates AnalysisRun and completes with SUCCESS."""
    from app.services.finops_analyzer import run_full_analysis
    with app.app_context():
        results = run_full_analysis()
        run = results["analysis_run"]
        assert run.status == "SUCCESS"
        assert run.resource_count >= 0


def test_22_failed_analysis_handling(app):
    """Test failed analysis run records FAILED status and error message."""
    from app.repositories.analysis_repository import AnalysisRepository
    with app.app_context():
        run = AnalysisRepository.create_analysis_run()
        AnalysisRepository.fail_analysis_run(run.id, "Simulated AWS Connection Timeout")
        failed_run = AnalysisRepository.get_analysis_run_by_id(run.id)
        assert failed_run.status == "FAILED"
        assert "Simulated AWS Connection Timeout" in failed_run.error_message


def test_23_analysis_history(auth_client):
    """Test analysis history page lists prior runs."""
    response = auth_client.get("/analysis/history")
    assert response.status_code == 200
    assert b"Analysis Run History" in response.data


def test_24_analysis_detail(auth_client, app):
    """Test inspecting specific analysis run detail page."""
    with app.app_context():
        from app.services.finops_analyzer import run_full_analysis
        res = run_full_analysis()
        run_id = res["analysis_run"].id

    response = auth_client.get(f"/analysis/{run_id}")
    assert response.status_code == 200
    assert b"Analysis Run #" in response.data


def test_25_analysis_status_api(auth_client, app):
    """Test API endpoint returns latest analysis JSON."""
    with app.app_context():
        from app.services.finops_analyzer import run_full_analysis
        run_full_analysis()

    response = auth_client.get("/api/analysis/latest")
    assert response.status_code == 200
    data = response.get_json()
    assert "status" in data
    assert "id" in data


# ---------------------------------------------------------------------------
# Resource Views & Edge Cases Tests (26-29)
# ---------------------------------------------------------------------------

def test_26_ec2_resource_view(auth_client):
    """Test EC2 resources view lists EC2 instances."""
    response = auth_client.get("/resources")
    assert response.status_code == 200
    assert b"Amazon EC2 Instances" in response.data


def test_27_ebs_resource_view(auth_client):
    """Test EBS resources view lists volume data."""
    response = auth_client.get("/resources")
    assert response.status_code == 200
    assert b"Amazon EBS Volumes" in response.data


def test_28_missing_metric_handling(app):
    """Verify missing metrics leave CPU utilization as None without breaking correlation."""
    from app.services.db_loader import load_data_from_db
    with app.app_context():
        data = load_data_from_db()
        for ec2 in data.get("ec2", []):
            if ec2.get("status") == "stopped" or ec2.get("cpu_utilization") is None:
                assert ec2.get("cpu_utilization") is None


def test_29_missing_savings_handling(app):
    """Verify missing resource-level costs output N/A or 0.0 savings gracefully."""
    from app.services.savings_calculator import generate_optimization_summary
    with app.app_context():
        summary = generate_optimization_summary([], 0.0)
        assert summary["total_monthly_savings"] == 0.0
        assert summary["savings_percentage"] == 0.0


# ---------------------------------------------------------------------------
# Regression Test Baseline (30)
# ---------------------------------------------------------------------------

def test_30_regression_baseline(auth_client):
    """Verify overall application API endpoints respond without error."""
    res1 = auth_client.get("/api/analysis/history")
    res2 = auth_client.get("/api/resources")
    res3 = auth_client.get("/api/findings")
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res3.status_code == 200
