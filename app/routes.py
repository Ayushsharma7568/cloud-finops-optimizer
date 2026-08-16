from flask import render_template


def register_routes(app):
    """Register all application routes."""

    @app.route("/")
    def index():
        return render_template("index.html")
