from flask import Flask
from config import Config


def create_app():
    """Application factory for the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    from app.extensions import db, migrate
    db.init_app(app)
    
    # Import models so Alembic can discover them
    with app.app_context():
        from app import models
        
    migrate.init_app(app, db)

    # Register routes
    from app.routes import register_routes

    register_routes(app)

    return app
