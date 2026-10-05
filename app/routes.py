import logging
from flask import render_template, jsonify
from app.services.finops_analyzer import run_full_analysis
from app.services.finops_reporting import (
    get_latest_analysis_summary,
    get_analysis_run_summary_by_id,
    get_recent_analysis_history,
)

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register all application routes."""

    @app.route("/")
    def index():
        try:
            results = run_full_analysis()
            summary = results["summary"]
            optimization = results["optimization"]
            error = None
        except Exception as e:
            logger.error("Failed to run analysis: %s", e)
            summary = None
            optimization = None
            error = str(e)

        return render_template(
            "index.html",
            summary=summary,
            optimization=optimization,
            error=error,
        )

    @app.route("/api/analysis/latest")
    def api_latest_analysis():
        """Get summary of the latest analysis run."""
        summary = get_latest_analysis_summary()
        if not summary:
            return jsonify({"error": "No analysis runs found"}), 404
        return jsonify(summary), 200

    @app.route("/api/analysis/history")
    def api_analysis_history():
        """Get history of recent analysis runs."""
        history = get_recent_analysis_history(limit=10)
        return jsonify(history), 200

    @app.route("/api/analysis/<int:run_id>")
    def api_analysis_by_id(run_id):
        """Get summary of a specific analysis run by ID."""
        summary = get_analysis_run_summary_by_id(run_id)
        if not summary:
            return jsonify({"error": f"Analysis run #{run_id} not found"}), 404
        return jsonify(summary), 200
