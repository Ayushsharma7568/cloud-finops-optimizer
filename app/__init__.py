import click
from flask import Flask
from flask_login import LoginManager
from config import Config
from app.services.security import generate_csrf_token

login_manager = LoginManager()


def create_app(test_config=None):
    """Application factory for the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if app.config.get("SECRET_KEY"):
        app.secret_key = app.config["SECRET_KEY"]

    # Initialize extensions
    from app.extensions import db, migrate
    db.init_app(app)

    # Setup Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message = "Please log in to access the Cloud FinOps Optimizer."
    login_manager.login_message_category = "warning"

    from app.repositories.user_repository import UserRepository

    @login_manager.user_loader
    def load_user(user_id):
        return UserRepository.get_user_by_id(user_id)

    @login_manager.unauthorized_handler
    def unauthorized_callback():
        from flask import request, jsonify, redirect, url_for
        if request.path.startswith("/api/"):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for("login", next=request.path))


    # Inject csrf_token helper into Jinja context
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf_token)

    # Import models so Alembic can discover them
    with app.app_context():
        from app import models

    migrate.init_app(app, db)

    # Register routes
    from app.routes import register_routes
    register_routes(app)

    # Register CLI commands
    @app.cli.command("create-user")
    @click.option("--username", prompt=True, help="Username")
    @click.option("--email", prompt=True, help="Email address")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Password")
    def create_user_cli(username, email, password):
        """CLI command to securely create an application user."""
        with app.app_context():
            if UserRepository.get_user_by_username(username):
                click.echo(f"Error: User with username '{username}' already exists.")
                return
            if UserRepository.get_user_by_email(email):
                click.echo(f"Error: User with email '{email}' already exists.")
                return

            user = UserRepository.create_user(username, email, password)
            click.echo(f"Successfully created user ID #{user.id} ({user.username})")

    return app
