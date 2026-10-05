"""Script for securely creating a local application user.

Usage:
    python scripts/create_user.py --username admin_user --email admin@example.com --password mysecretpass
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.repositories.user_repository import UserRepository


def main():
    parser = argparse.ArgumentParser(description="Create a Cloud FinOps Optimizer user.")
    parser.add_argument("--username", required=True, help="Username")
    parser.add_argument("--email", required=True, help="Email address")
    parser.add_argument("--password", required=True, help="User password")

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if UserRepository.get_user_by_username(args.username):
            print(f"Error: User with username '{args.username}' already exists.")
            sys.exit(1)

        if UserRepository.get_user_by_email(args.email):
            print(f"Error: User with email '{args.email}' already exists.")
            sys.exit(1)

        user = UserRepository.create_user(args.username, args.email, args.password)
        print(f"Successfully created user ID #{user.id} (username: {user.username}, email: {user.email})")


if __name__ == "__main__":
    main()
