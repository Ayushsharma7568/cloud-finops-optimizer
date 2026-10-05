from app.extensions import db
from app.models import User


class UserRepository:
    """Repository for user management and authentication persistence operations."""

    @staticmethod
    def create_user(username: str, email: str, password: str) -> User:
        """Create and persist a new user record with hashed password."""
        user = User(username=username.strip(), email=email.strip().lower())
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def get_user_by_id(user_id: int) -> User | None:
        """Retrieve user by primary key ID."""
        if hasattr(db.session, "get"):
            return db.session.get(User, user_id)
        return User.query.get(int(user_id))

    @staticmethod
    def get_user_by_username(username: str) -> User | None:
        """Retrieve user by username."""
        return User.query.filter_by(username=username.strip()).first()

    @staticmethod
    def get_user_by_email(email: str) -> User | None:
        """Retrieve user by email address."""
        return User.query.filter_by(email=email.strip().lower()).first()

    @staticmethod
    def get_user_by_username_or_email(identifier: str) -> User | None:
        """Retrieve user matching username or email."""
        clean_id = identifier.strip()
        return User.query.filter(
            (User.username == clean_id) | (User.email == clean_id.lower())
        ).first()

    @staticmethod
    def verify_credentials(identifier: str, password: str) -> User | None:
        """Verify user credentials against stored password hash.

        Returns User if password matches, else None.
        """
        user = UserRepository.get_user_by_username_or_email(identifier)
        if user and user.check_password(password):
            return user
        return None
