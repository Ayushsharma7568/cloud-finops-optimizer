import logging

from flask import render_template

from app.services.data_loader import load_all_data, DataLoadError
from app.services.cost_analysis import generate_summary
from app.services.waste_detector import detect_findings
from app.services.recommendation_engine import generate_recommendations
from app.services.savings_calculator import generate_optimization_summary

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register all application routes."""

    @app.route("/")
    def index():
        try:
            data = load_all_data()
            summary = generate_summary(data)

            findings = detect_findings(data)
            recommendations = generate_recommendations(findings)
            optimization = generate_optimization_summary(
                recommendations, summary["costs"]["total"]
            )
            error = None
        except DataLoadError as e:
            logger.error("Failed to load cloud data: %s", e)
            summary = None
            optimization = None
            error = str(e)

        return render_template(
            "index.html",
            summary=summary,
            optimization=optimization,
            error=error,
        )
