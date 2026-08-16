from flask import Flask
from config import Config


def create_app():
    """Application factory for the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register routes
    from app.routes import register_routes

    register_routes(app)

    return app
