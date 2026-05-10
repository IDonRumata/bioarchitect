"""initial schema: users, user_profiles, consent_records.

Revision ID: 20260509_1200
Revises:
Create Date: 2026-05-09 12:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260509_1200"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- ENUM-типы ---
    op.execute("CREATE TYPE user_status AS ENUM ('active', 'suspended', 'pending_deletion', 'deleted')")
    op.execute("CREATE TYPE sex AS ENUM ('male', 'female', 'unspecified')")
    op.execute(
        "CREATE TYPE work_pattern AS ENUM "
        "('long_haul', 'shift_work', 'mixed', 'office', 'unspecified')"
    )
    op.execute(
        "CREATE TYPE consent_type AS ENUM "
        "('terms_of_service', 'health_data_processing', 'analytics', "
        "'marketing', 'lab_report_storage')"
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("country_iso", sa.String(length=2), nullable=True),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="ru"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active", "suspended", "pending_deletion", "deleted",
                name="user_status",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("onboarding_completed_at", sa.DateTime(), nullable=True),
        sa.Column("deletion_requested_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "country_iso IS NULL OR length(country_iso) = 2",
            name="ck_users_country_iso_alpha2",
        ),
        sa.CheckConstraint(
            "locale IN ('ru', 'en', 'pl', 'de')",
            name="ck_users_locale_supported",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index(
        "ix_users_status_active",
        "users",
        ["status"],
        postgresql_where=sa.text("status = 'active'"),
    )

    # --- user_profiles ---
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "sex",
            postgresql.ENUM(
                "male", "female", "unspecified",
                name="sex",
                create_type=False,
            ),
            nullable=False,
            server_default="unspecified",
        ),
        sa.Column("birth_year", sa.SmallInteger(), nullable=True),
        sa.Column("height_cm", sa.SmallInteger(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column(
            "work_pattern",
            postgresql.ENUM(
                "long_haul", "shift_work", "mixed", "office", "unspecified",
                name="work_pattern",
                create_type=False,
            ),
            nullable=False,
            server_default="unspecified",
        ),
        sa.Column(
            "lifestyle_tags",
            postgresql.ARRAY(sa.String(length=32)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "birth_year IS NULL OR (birth_year >= 1900 AND birth_year <= 2008)",
            name="ck_user_profiles_birth_year_range",
        ),
        sa.CheckConstraint(
            "height_cm IS NULL OR (height_cm >= 100 AND height_cm <= 250)",
            name="ck_user_profiles_height_cm_range",
        ),
        sa.CheckConstraint(
            "weight_kg IS NULL OR (weight_kg >= 30 AND weight_kg <= 300)",
            name="ck_user_profiles_weight_kg_range",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_user_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_profiles"),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    # --- consent_records ---
    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "consent_type",
            postgresql.ENUM(
                "terms_of_service", "health_data_processing", "analytics",
                "marketing", "lab_report_storage",
                name="consent_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("version", sa.String(length=16), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=256), nullable=True),
        sa.Column("notes", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_consent_records_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_consent_records"),
    )
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])
    op.create_index(
        "ix_consent_records_user_type_time",
        "consent_records",
        ["user_id", "consent_type", "granted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_consent_records_user_type_time", table_name="consent_records")
    op.drop_index("ix_consent_records_user_id", table_name="consent_records")
    op.drop_table("consent_records")

    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")

    op.drop_index("ix_users_status_active", table_name="users")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE consent_type")
    op.execute("DROP TYPE work_pattern")
    op.execute("DROP TYPE sex")
    op.execute("DROP TYPE user_status")
