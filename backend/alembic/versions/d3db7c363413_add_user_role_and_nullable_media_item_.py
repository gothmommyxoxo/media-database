"""add user role and nullable media_item added_by

Revision ID: d3db7c363413
Revises: e7b8f044a33e
Create Date: 2026-08-05 15:29:58.376118

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3db7c363413'
down_revision: Union[str, None] = 'e7b8f044a33e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing rows (e.g. the seed-script account already created in a running deployment) need a
    # default so this is safe against a live table, not just a fresh one -- every pre-existing
    # account becomes MEMBER; promote the intended admin(s) manually after migrating (13's
    # rationale covers only the *seed script's* first-run default, not a mid-flight upgrade).
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.Enum("ADMIN", "MEMBER", name="role", native_enum=False, length=10),
                nullable=False,
                server_default="MEMBER",
            )
        )

    # Only relaxes the NOT NULL constraint. The FK's ON DELETE SET NULL behavior added to the
    # model is enforced in application code (AdminUserService.delete_user, 4.1), not depended on
    # at the database level, so the original (unnamed, plain) FK constraint is left untouched
    # rather than guessing its auto-generated name to drop and recreate it.
    with op.batch_alter_table("media_items") as batch_op:
        batch_op.alter_column("added_by", existing_type=sa.INTEGER(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("media_items") as batch_op:
        batch_op.alter_column("added_by", existing_type=sa.INTEGER(), nullable=False)

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("role")
