from flask import render_template


def register_routes(app):
    """Register all application routes."""

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/resources")
    def resources():
        return render_template("resources.html")

    @app.route("/recommendations")
    def recommendations():
        return render_template("recommendations.html")
