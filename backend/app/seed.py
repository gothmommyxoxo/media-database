"""One-time seed script to create the first household account (Section 4).

Usage: python -m app.seed <username> <display_name> <password>

The first account is always created as ADMIN (13's rationale: whoever can run this script
already has more access than the app's admin role grants). Additional accounts are created
through the admin panel (4.1), not this script.
"""

import sys

from app.auth.security import hash_password
from app.db import SessionLocal
from app.models import Role, User


def create_first_user(username: str, display_name: str, password: str) -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first() is not None:
            print(f"User '{username}' already exists.")
            return
        user = User(
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            role=Role.ADMIN,
        )
        db.add(user)
        db.commit()
        print(f"Created admin user '{username}' (id={user.id}).")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python -m app.seed <username> <display_name> <password>")
        sys.exit(1)
    create_first_user(sys.argv[1], sys.argv[2], sys.argv[3])
