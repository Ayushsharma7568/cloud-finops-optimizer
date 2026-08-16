import logging

from flask import render_template

from app.services.data_loader import load_all_data, DataLoadError
from app.services.cost_analysis import generate_summary

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register all application routes."""

    @app.route("/")
    def index():
        try:
            data = load_all_data()
            summary = generate_summary(data)
            error = None
        except DataLoadError as e:
            logger.error("Failed to load cloud data: %s", e)
            summary = None
            error = str(e)

        return render_template("index.html", summary=summary, error=error)
