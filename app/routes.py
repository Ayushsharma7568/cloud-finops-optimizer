import logging
from flask import render_template
from app.services.finops_analyzer import run_full_analysis

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
