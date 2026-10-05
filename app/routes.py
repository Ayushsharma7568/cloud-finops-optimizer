import logging
from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)

from app.repositories.user_repository import UserRepository
from app.services.finops_analyzer import run_full_analysis
from app.services.finops_reporting import (
    get_latest_analysis_summary,
    get_analysis_run_summary_by_id,
    get_recent_analysis_history,
)
from app.services.db_loader import load_data_from_db
from app.services.cost_analysis import generate_summary
from app.services.waste_detector import detect_findings
from app.services.recommendation_engine import generate_recommendations
from app.services.savings_calculator import generate_optimization_summary
from app.services.security import validate_csrf_token

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register all application routes."""

    # -----------------------------------------------------------------------
    # Authentication Routes
    # -----------------------------------------------------------------------

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        error = None
        if request.method == "POST":
            # CSRF token check
            token = request.form.get("csrf_token")
            if not validate_csrf_token(token):
                error = "Security token invalid or expired. Please try again."
            else:
                identifier = request.form.get("identifier", "").strip()
                password = request.form.get("password", "")

                user = UserRepository.verify_credentials(identifier, password)
                if user:
                    login_user(user)
                    logger.info("User '%s' logged in successfully.", user.username)
                    next_page = request.args.get("next")
                    if next_page and next_page.startswith("/"):
                        return redirect(next_page)
                    return redirect(url_for("index"))
                else:
                    # Generic error message to avoid username enumeration
                    error = "Invalid username/email or password."

        return render_template("login.html", error=error), 400 if error else 200

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        token = request.form.get("csrf_token")
        if not validate_csrf_token(token):
            flash("Security token invalid.", "danger")
            return redirect(url_for("index"))

        user_name = current_user.username if current_user else "User"
        logout_user()
        logger.info("User '%s' logged out.", user_name)
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    # -----------------------------------------------------------------------
    # Protected FinOps Dashboard & Application Views
    # -----------------------------------------------------------------------

    @app.route("/")
    @app.route("/dashboard")
    @login_required
    def index():
        try:
            latest_summary = get_latest_analysis_summary()
            data = load_data_from_db()
            summary = generate_summary(data)
            findings = detect_findings(data)
            recommendations = generate_recommendations(findings)
            optimization = generate_optimization_summary(
                recommendations, summary["costs"]["total"]
            )
            history = get_recent_analysis_history(limit=5)
            error = None
        except Exception as e:
            logger.error("Failed to load dashboard: %s", e)
            summary = None
            optimization = None
            findings = []
            recommendations = []
            history = []
            latest_summary = None
            error = "Unable to load complete FinOps dashboard data. Please run analysis."

        return render_template(
            "index.html",
            summary=summary,
            optimization=optimization,
            findings=findings,
            recommendations=recommendations,
            history=history,
            latest_summary=latest_summary,
            error=error,
        )

    @app.route("/analysis/run", methods=["POST"])
    @login_required
    def trigger_analysis():
        token = request.form.get("csrf_token")
        if not validate_csrf_token(token):
            flash("Security token invalid.", "danger")
            return redirect(url_for("index"))

        try:
            results = run_full_analysis()
            run_id = results["analysis_run"].id
            flash(f"AWS Analysis Run #{run_id} completed successfully!", "success")
            return redirect(url_for("analysis_detail", run_id=run_id))
        except Exception as e:
            logger.error("Analysis run failed: %s", e)
            flash(f"Analysis failed: {e}", "danger")
            return redirect(url_for("index"))

    @app.route("/resources")
    @login_required
    def resources_view():
        data = load_data_from_db()
        ec2_list = data.get("ec2", [])
        ebs_list = data.get("ebs", [])
        s3_list = data.get("s3", [])

        return render_template(
            "resources.html",
            ec2_list=ec2_list,
            ebs_list=ebs_list,
            s3_list=s3_list,
            metrics=data.get("summary_metrics", {}),
        )

    @app.route("/findings")
    @login_required
    def findings_view():
        data = load_data_from_db()
        findings = detect_findings(data)
        severity_filter = request.args.get("severity")
        resource_type_filter = request.args.get("resource_type")

        if severity_filter:
            findings = [f for f in findings if getattr(f.severity, "value", str(f.severity)) == severity_filter]
        if resource_type_filter:
            findings = [f for f in findings if f.resource_type == resource_type_filter]

        return render_template(
            "findings.html",
            findings=findings,
            severity_filter=severity_filter,
            resource_type_filter=resource_type_filter,
        )

    @app.route("/recommendations")
    @login_required
    def recommendations_view():
        data = load_data_from_db()
        findings = detect_findings(data)
        recommendations = generate_recommendations(findings)

        return render_template(
            "recommendations.html",
            recommendations=recommendations,
        )

    @app.route("/analysis/history")
    @login_required
    def analysis_history():
        history = get_recent_analysis_history(limit=20)
        return render_template("history.html", history=history)

    @app.route("/analysis/<int:run_id>")
    @login_required
    def analysis_detail(run_id):
        summary = get_analysis_run_summary_by_id(run_id)
        if not summary:
            flash(f"Analysis Run #{run_id} not found.", "warning")
            return redirect(url_for("analysis_history"))

        return render_template("analysis_detail.html", summary=summary)

    # -----------------------------------------------------------------------
    # Protected FinOps REST APIs
    # -----------------------------------------------------------------------

    @app.route("/api/analysis/latest")
    @login_required
    def api_latest_analysis():
        summary = get_latest_analysis_summary()
        if not summary:
            return jsonify({"error": "No analysis runs found"}), 404
        return jsonify(summary), 200

    @app.route("/api/analysis/history")
    @login_required
    def api_analysis_history():
        history = get_recent_analysis_history(limit=10)
        return jsonify(history), 200

    @app.route("/api/analysis/<int:run_id>")
    @login_required
    def api_analysis_by_id(run_id):
        summary = get_analysis_run_summary_by_id(run_id)
        if not summary:
            return jsonify({"error": f"Analysis run #{run_id} not found"}), 404
        return jsonify(summary), 200

    @app.route("/api/resources")
    @login_required
    def api_resources():
        data = load_data_from_db()
        return jsonify(data), 200

    @app.route("/api/findings")
    @login_required
    def api_findings():
        data = load_data_from_db()
        findings = detect_findings(data)
        return jsonify([f.to_dict() for f in findings]), 200
