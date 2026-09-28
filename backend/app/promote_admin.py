"""One-time operational script to promote an existing account to ADMIN.

Needed after upgrading a database that had users before the role migration (d3db7c363413)
ran -- every pre-existing account becomes MEMBER by default (see that migration's comment).

Usage: python -m app.promote_admin <username>
"""

import sys

from app.db import SessionLocal
from app.models import Role, User


def promote(username: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            print(f"No such user '{username}'.")
            return
        if user.role == Role.ADMIN:
            print(f"'{username}' is already an admin.")
            return
        user.role = Role.ADMIN
        db.commit()
        print(f"Promoted '{username}' to admin.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.promote_admin <username>")
        sys.exit(1)
    promote(sys.argv[1])
