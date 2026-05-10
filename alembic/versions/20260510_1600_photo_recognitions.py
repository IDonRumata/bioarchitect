"""Vision Phase 1: photo_recognitions table.

Revision ID: 20260510_1600
Revises: 20260510_1400
Create Date: 2026-05-10 16:00:00

Что делаем:
    - Таблица photo_recognitions: pHash-кэш результатов Vision API.
    - Фото не хранится (photo_kept = false, GDPR Art. 5(1)(c)).
    - Составные индексы для поиска кэша по (user_id, phash) и (user_id, created_at).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260510_1600"
down_revision = "20260510_1400"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "photo_recognitions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 64-bit pHash в hex (16 символов).
        sa.Column("phash", sa.String(16), nullable=False),
        # JSON-массив RecognizedItem.
        sa.Column("items_json", sa.Text, nullable=False),
        sa.Column("overall_confidence", sa.Float, nullable=False),
        sa.Column("cost_cents", sa.Float, nullable=False, server_default="0"),
        sa.Column("llm_model", sa.String(64), nullable=False),
        # Всегда false — фото не хранится.
        sa.Column(
            "photo_kept",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "overall_confidence >= 0.0 AND overall_confidence <= 1.0",
            name="ck_photo_recognitions_confidence",
        ),
    )

    op.create_index(
        "ix_photo_recognitions_user_phash",
        "photo_recognitions",
        ["user_id", "phash"],
    )
    op.create_index(
        "ix_photo_recognitions_user_created",
        "photo_recognitions",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_photo_recognitions_user_created", "photo_recognitions")
    op.drop_index("ix_photo_recognitions_user_phash", "photo_recognitions")
    op.drop_table("photo_recognitions")
