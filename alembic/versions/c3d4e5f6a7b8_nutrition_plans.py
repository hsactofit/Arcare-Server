"""Add nutrition_plans table for AI-generated meal plans (1 per user per day)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-16 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "nutrition_plans" in inspector.get_table_names():
        return

    op.create_table(
        "nutrition_plans",
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
        sa.UniqueConstraint("user_id", "plan_date", name="uq_nutrition_plans_user_date"),
    )
    op.create_index(op.f("ix_nutrition_plans_id"), "nutrition_plans", ["id"], unique=False)
    op.create_index(op.f("ix_nutrition_plans_user_id"), "nutrition_plans", ["user_id"], unique=False)
    op.create_index(op.f("ix_nutrition_plans_plan_date"), "nutrition_plans", ["plan_date"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "nutrition_plans" not in inspector.get_table_names():
        return
    op.drop_index(op.f("ix_nutrition_plans_plan_date"), table_name="nutrition_plans")
    op.drop_index(op.f("ix_nutrition_plans_user_id"), table_name="nutrition_plans")
    op.drop_index(op.f("ix_nutrition_plans_id"), table_name="nutrition_plans")
    op.drop_table("nutrition_plans")
