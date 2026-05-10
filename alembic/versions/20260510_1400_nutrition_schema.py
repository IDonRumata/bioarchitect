"""nutrition schema: food_items, food_aliases, food_logs (partitioned).

Revision ID: 20260510_1400
Revises: 20260509_1200
Create Date: 2026-05-10 14:00:00

Что делаем:
    - CREATE EXTENSION pg_trgm (для fuzzy-поиска по food_aliases.alias).
    - ENUM food_source, food_log_method.
    - food_items + GIN trgm index на name.
    - food_aliases + GIN trgm index на alias.
    - food_logs PARTITIONED BY RANGE (logged_at), 12 партиций на 2026 +
      DEFAULT-партиция (для логов до 2026 и после декабря 2026, чтобы
      сидинг тестов и edge-cases не падали).
    - BEFORE UPDATE trigger на food_logs (immutable). DELETE разрешён —
      нужен для GDPR CASCADE при удалении пользователя.

Партиции на 2027+ создаём отдельной миграцией ближе к делу — это рутинная
ARQ-операция, и нет смысла делать партиции на годы вперёд (raises ALTER
TABLE locks при autovacuum).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260510_1400"
down_revision: str | None = "20260509_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Месячные партиции food_logs на 2026.
_PARTITIONS_2026 = [
    ("food_logs_2026_01", "2026-01-01", "2026-02-01"),
    ("food_logs_2026_02", "2026-02-01", "2026-03-01"),
    ("food_logs_2026_03", "2026-03-01", "2026-04-01"),
    ("food_logs_2026_04", "2026-04-01", "2026-05-01"),
    ("food_logs_2026_05", "2026-05-01", "2026-06-01"),
    ("food_logs_2026_06", "2026-06-01", "2026-07-01"),
    ("food_logs_2026_07", "2026-07-01", "2026-08-01"),
    ("food_logs_2026_08", "2026-08-01", "2026-09-01"),
    ("food_logs_2026_09", "2026-09-01", "2026-10-01"),
    ("food_logs_2026_10", "2026-10-01", "2026-11-01"),
    ("food_logs_2026_11", "2026-11-01", "2026-12-01"),
    ("food_logs_2026_12", "2026-12-01", "2027-01-01"),
]


def upgrade() -> None:
    # --- pg_trgm extension ---
    # Требует superuser в Postgres. В docker-compose dev-контейнер запускается
    # под postgres-юзером, у которого superuser есть. На продакшне Андрей
    # вручную запустит CREATE EXTENSION под suo (см. docs/setup/).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # --- ENUM-типы ---
    op.execute(
        "CREATE TYPE food_source AS ENUM ('usda', 'off', 'chain', 'manual')"
    )
    op.execute(
        "CREATE TYPE food_log_method AS ENUM "
        "('text_input', 'photo_phase1', 'photo_phase2', 'chain_menu', 'quick_repeat')"
    )

    # --- food_items ---
    op.create_table(
        "food_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source",
            postgresql.ENUM(
                "usda", "off", "chain", "manual",
                name="food_source",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("brand", sa.String(length=128), nullable=True),
        sa.Column("kcal_100g", sa.Float(), nullable=False),
        sa.Column("protein_100g", sa.Float(), nullable=False),
        sa.Column("fat_100g", sa.Float(), nullable=False),
        sa.Column("carbs_100g", sa.Float(), nullable=False),
        sa.Column("fiber_100g", sa.Float(), nullable=True),
        sa.Column("serving_g", sa.Float(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kcal_100g >= 0 AND kcal_100g <= 1000",
            name="ck_food_items_kcal_range",
        ),
        sa.CheckConstraint(
            "protein_100g >= 0 AND fat_100g >= 0 AND carbs_100g >= 0",
            name="ck_food_items_macros_nonneg",
        ),
        sa.CheckConstraint(
            "fiber_100g IS NULL OR fiber_100g >= 0",
            name="ck_food_items_fiber_nonneg",
        ),
        sa.CheckConstraint(
            "serving_g IS NULL OR (serving_g > 0 AND serving_g <= 5000)",
            name="ck_food_items_serving_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_food_items"),
        sa.UniqueConstraint("source", "external_id", name="uq_food_items_source_external"),
    )
    # GIN trgm на lower(name) — поиск case-insensitive.
    op.execute(
        "CREATE INDEX ix_food_items_name_trgm ON food_items "
        "USING GIN (lower(name) gin_trgm_ops)"
    )
    op.create_index("ix_food_items_source", "food_items", ["source"])

    # --- food_aliases ---
    op.create_table(
        "food_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("food_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("alias", sa.String(length=256), nullable=False),
        sa.CheckConstraint(
            "locale IN ('ru', 'en', 'pl', 'de')",
            name="ck_food_aliases_locale_supported",
        ),
        sa.ForeignKeyConstraint(
            ["food_item_id"], ["food_items.id"],
            name="fk_food_aliases_food_item_id_food_items",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_food_aliases"),
        sa.UniqueConstraint(
            "food_item_id", "locale", "alias",
            name="uq_food_aliases_item_locale_alias",
        ),
    )
    op.create_index("ix_food_aliases_food_item_id", "food_aliases", ["food_item_id"])
    op.execute(
        "CREATE INDEX ix_food_aliases_alias_trgm ON food_aliases "
        "USING GIN (lower(alias) gin_trgm_ops)"
    )
    # B-tree для locale — мы фильтруем по нему перед similarity.
    op.create_index("ix_food_aliases_locale", "food_aliases", ["locale"])

    # --- food_logs (partitioned parent) ---
    # Создаём через raw SQL — Alembic op.create_table не поддерживает
    # PARTITION BY декларативно.
    op.execute(
        """
        CREATE TABLE food_logs (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            food_item_id UUID NOT NULL,
            grams DOUBLE PRECISION NOT NULL,
            kcal DOUBLE PRECISION NOT NULL,
            protein_g DOUBLE PRECISION NOT NULL,
            fat_g DOUBLE PRECISION NOT NULL,
            carbs_g DOUBLE PRECISION NOT NULL,
            method food_log_method NOT NULL,
            raw_input VARCHAR(512),
            logged_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT pk_food_logs PRIMARY KEY (id, logged_at),
            CONSTRAINT ck_food_logs_grams_range
                CHECK (grams > 0 AND grams <= 5000),
            CONSTRAINT ck_food_logs_nutrients_nonneg
                CHECK (kcal >= 0 AND protein_g >= 0 AND fat_g >= 0 AND carbs_g >= 0),
            CONSTRAINT fk_food_logs_user_id_users
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_food_logs_food_item_id_food_items
                FOREIGN KEY (food_item_id) REFERENCES food_items(id) ON DELETE RESTRICT
        ) PARTITION BY RANGE (logged_at)
        """
    )

    # Месячные партиции на 2026 + DEFAULT.
    for name, lo, hi in _PARTITIONS_2026:
        op.execute(
            f"CREATE TABLE {name} PARTITION OF food_logs "
            f"FOR VALUES FROM ('{lo}') TO ('{hi}')"
        )
    op.execute("CREATE TABLE food_logs_default PARTITION OF food_logs DEFAULT")

    op.execute(
        "CREATE INDEX ix_food_logs_user_logged ON food_logs (user_id, logged_at)"
    )

    # --- Append-only trigger ---
    # food_logs immutable: запрет UPDATE. DELETE разрешён (GDPR CASCADE).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION food_logs_block_update()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'food_logs is append-only (immutable health data, GDPR audit)';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_food_logs_block_update
        BEFORE UPDATE ON food_logs
        FOR EACH ROW EXECUTE FUNCTION food_logs_block_update()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_food_logs_block_update ON food_logs")
    op.execute("DROP FUNCTION IF EXISTS food_logs_block_update()")

    op.execute("DROP INDEX IF EXISTS ix_food_logs_user_logged")
    # Дроп родительской партиционной таблицы — каскадно дропает все партиции.
    op.execute("DROP TABLE IF EXISTS food_logs CASCADE")

    op.drop_index("ix_food_aliases_locale", table_name="food_aliases")
    op.execute("DROP INDEX IF EXISTS ix_food_aliases_alias_trgm")
    op.drop_index("ix_food_aliases_food_item_id", table_name="food_aliases")
    op.drop_table("food_aliases")

    op.drop_index("ix_food_items_source", table_name="food_items")
    op.execute("DROP INDEX IF EXISTS ix_food_items_name_trgm")
    op.drop_table("food_items")

    op.execute("DROP TYPE IF EXISTS food_log_method")
    op.execute("DROP TYPE IF EXISTS food_source")

    # pg_trgm намеренно НЕ дропаем — он может использоваться и другими
    # таблицами (например, OCR Lab аналитами в спринте 10).


# Удобная константа для будущей миграции 2027+.
# Когда будет нужно добавить партиции на следующий год — копируем шаблон
# из ARQ-воркера в спринте 6 (там же будет автоматизация).
__all__ = ["_PARTITIONS_2026"]
