"""SOS contacts table + simplify sos_configs for emergency numbers only

Revision ID: a1b2c3d4e5f6
Revises: 3acf33a62782
Create Date: 2026-07-15 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "3acf33a62782"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    # Ensure sos_configs exists (may have been created via Base.metadata.create_all)
    if "sos_configs" not in tables:
        op.create_table(
            "sos_configs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("police_number", sa.String(length=50), nullable=False, server_default="112"),
            sa.Column("ambulance_number", sa.String(length=50), nullable=False, server_default="102"),
            sa.Column("fire_number", sa.String(length=50), nullable=False, server_default="101"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )
        op.create_index(op.f("ix_sos_configs_id"), "sos_configs", ["id"], unique=False)
    else:
        cols = {c["name"] for c in inspector.get_columns("sos_configs")}

        # Create sos_contacts and migrate fixed contact1/2/3 columns if present
        if "sos_contacts" not in tables:
            op.create_table(
                "sos_contacts",
                sa.Column("id", sa.Integer(), nullable=False),
                sa.Column("user_id", sa.Integer(), nullable=False),
                sa.Column("name", sa.String(length=255), nullable=False),
                sa.Column("phone", sa.String(length=50), nullable=False),
                sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
                sa.PrimaryKeyConstraint("id"),
            )
            op.create_index(op.f("ix_sos_contacts_id"), "sos_contacts", ["id"], unique=False)
            op.create_index(op.f("ix_sos_contacts_user_id"), "sos_contacts", ["user_id"], unique=False)

            if "contact1_name" in cols:
                # Migrate existing fixed contacts into sos_contacts
                op.execute(
                    """
                    INSERT INTO sos_contacts (user_id, name, phone)
                    SELECT user_id, contact1_name, contact1_phone FROM sos_configs
                    WHERE contact1_name IS NOT NULL AND contact1_phone IS NOT NULL
                    UNION ALL
                    SELECT user_id, contact2_name, contact2_phone FROM sos_configs
                    WHERE contact2_name IS NOT NULL AND contact2_phone IS NOT NULL
                    UNION ALL
                    SELECT user_id, contact3_name, contact3_phone FROM sos_configs
                    WHERE contact3_name IS NOT NULL AND contact3_phone IS NOT NULL
                    """
                )

                # Drop fixed contact columns
                for col in (
                    "contact1_name",
                    "contact1_phone",
                    "contact2_name",
                    "contact2_phone",
                    "contact3_name",
                    "contact3_phone",
                ):
                    if col in cols:
                        op.drop_column("sos_configs", col)

    # Ensure sos_contacts exists even if sos_configs was just created above
    inspector = inspect(bind)
    if "sos_contacts" not in inspector.get_table_names():
        op.create_table(
            "sos_contacts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=50), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_sos_contacts_id"), "sos_contacts", ["id"], unique=False)
        op.create_index(op.f("ix_sos_contacts_user_id"), "sos_contacts", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if "sos_contacts" in tables:
        # Re-add fixed contact columns on sos_configs if missing
        if "sos_configs" in tables:
            cols = {c["name"] for c in inspector.get_columns("sos_configs")}
            for col, length in (
                ("contact1_name", 255),
                ("contact1_phone", 50),
                ("contact2_name", 255),
                ("contact2_phone", 50),
                ("contact3_name", 255),
                ("contact3_phone", 50),
            ):
                if col not in cols:
                    op.add_column(
                        "sos_configs",
                        sa.Column(col, sa.String(length=length), nullable=True),
                    )

        op.drop_index(op.f("ix_sos_contacts_user_id"), table_name="sos_contacts")
        op.drop_index(op.f("ix_sos_contacts_id"), table_name="sos_contacts")
        op.drop_table("sos_contacts")
