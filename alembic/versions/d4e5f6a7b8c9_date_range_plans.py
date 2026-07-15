"""Rebuild workout_plans and nutrition_plans for start/end date range model

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-16 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_if_exists(name: str) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if name in inspector.get_table_names():
        op.drop_table(name)


def upgrade() -> None:
    # Full rebuild — previous schema was questionnaire/plan_date based
    _drop_if_exists("workout_plans")
    _drop_if_exists("nutrition_plans")

    op.create_table(
        "workout_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_plans_id"), "workout_plans", ["id"], unique=False)
    op.create_index(op.f("ix_workout_plans_user_id"), "workout_plans", ["user_id"], unique=False)
    op.create_index(op.f("ix_workout_plans_start_date"), "workout_plans", ["start_date"], unique=False)
    op.create_index(op.f("ix_workout_plans_end_date"), "workout_plans", ["end_date"], unique=False)

    op.create_table(
        "nutrition_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("daily_calories_target", sa.Integer(), nullable=True),
        sa.Column("days", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_nutrition_plans_id"), "nutrition_plans", ["id"], unique=False)
    op.create_index(op.f("ix_nutrition_plans_user_id"), "nutrition_plans", ["user_id"], unique=False)
    op.create_index(op.f("ix_nutrition_plans_start_date"), "nutrition_plans", ["start_date"], unique=False)
    op.create_index(op.f("ix_nutrition_plans_end_date"), "nutrition_plans", ["end_date"], unique=False)


def downgrade() -> None:
    _drop_if_exists("nutrition_plans")
    _drop_if_exists("workout_plans")
