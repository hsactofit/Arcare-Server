"""Add workout_plans table for AI-generated plans (1 per user per day)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-16 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "workout_plans" in inspector.get_table_names():
        return

    op.create_table(
        "workout_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("questionnaire_answers", sa.JSON(), nullable=False),
        sa.Column("plan_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "plan_date", name="uq_workout_plans_user_date"),
    )
    op.create_index(op.f("ix_workout_plans_id"), "workout_plans", ["id"], unique=False)
    op.create_index(op.f("ix_workout_plans_user_id"), "workout_plans", ["user_id"], unique=False)
    op.create_index(op.f("ix_workout_plans_plan_date"), "workout_plans", ["plan_date"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "workout_plans" not in inspector.get_table_names():
        return
    op.drop_index(op.f("ix_workout_plans_plan_date"), table_name="workout_plans")
    op.drop_index(op.f("ix_workout_plans_user_id"), table_name="workout_plans")
    op.drop_index(op.f("ix_workout_plans_id"), table_name="workout_plans")
    op.drop_table("workout_plans")
