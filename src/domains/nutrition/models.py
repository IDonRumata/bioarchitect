"""Модели домена nutrition.

Таблицы:
    - food_items     — справочник продуктов (USDA + Open Food Facts + chain).
    - food_aliases   — мультиязычные синонимы для fuzzy-поиска (pg_trgm).
    - food_logs      — журнал съеденного. Append-only, partitioned by month
      (RANGE по logged_at). Trigger блокирует UPDATE; DELETE разрешён только
      через CASCADE при удалении пользователя (GDPR Art. 17).

Принципы:
    - **Snapshot-нутриенты в food_logs.** kcal/protein/fat/carbs хранятся
      на момент логирования. Если food_items позже отредактируют, старые
      логи остаются неизменными — это требование ТЗ §5 (immutable health data).
    - **pg_trgm** используется только в food_aliases — там оригинальные
      пользовательские строки на 4 языках. food_items.name — каноническая
      английская строка, поиск по ней не основной.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.domains.nutrition.enums import FoodLogMethod, FoodSource

food_source_enum = ENUM(
    FoodSource,
    name="food_source",
    values_callable=lambda x: [e.value for e in x],
    create_type=False,
)

food_log_method_enum = ENUM(
    FoodLogMethod,
    name="food_log_method",
    values_callable=lambda x: [e.value for e in x],
    create_type=False,
)


class FoodItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Каноническая запись продукта.

    КБЖУ нормированы на 100 г. Если в источнике указана только порция —
    пересчитываем при сидинге.
    """

    __tablename__ = "food_items"

    source: Mapped[FoodSource] = mapped_column(food_source_enum, nullable=False)
    # Идентификатор в источнике (FDC ID для USDA, code для Open Food Facts).
    # Для source=manual — NULL.
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Каноническое английское название. Для не-английских записей USDA/OFF
    # дублируется в food_aliases (locale=en).
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # КБЖУ на 100 г.
    kcal_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_100g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Стандартный размер порции (если указан источником) — например, 1 яблоко = 182 г.
    serving_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    # verified=true — проверено медэдвайзером / редактором (выше в ранкинге).
    verified: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=text("false"),
    )

    aliases: Mapped[list["FoodAlias"]] = relationship(
        back_populates="food_item",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_food_items_source_external"),
        CheckConstraint(
            "kcal_100g >= 0 AND kcal_100g <= 1000",
            name="ck_food_items_kcal_range",
        ),
        CheckConstraint(
            "protein_100g >= 0 AND fat_100g >= 0 AND carbs_100g >= 0",
            name="ck_food_items_macros_nonneg",
        ),
        CheckConstraint(
            "fiber_100g IS NULL OR fiber_100g >= 0",
            name="ck_food_items_fiber_nonneg",
        ),
        CheckConstraint(
            "serving_g IS NULL OR (serving_g > 0 AND serving_g <= 5000)",
            name="ck_food_items_serving_range",
        ),
        # GIN trgm-индекс на name создаётся в миграции (SQLAlchemy не умеет
        # ops-классы из коробки в декларативе).
    )

    def __repr__(self) -> str:
        return f"<FoodItem id={self.id} source={self.source.value} name={self.name!r}>"


class FoodAlias(Base, UUIDPrimaryKeyMixin):
    """Мультиязычный синоним для fuzzy-поиска.

    Несколько алиасов на один FoodItem (например, «куриная грудка»,
    «грудка курицы», «филе грудки» → один FoodItem).
    """

    __tablename__ = "food_aliases"

    food_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("food_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    alias: Mapped[str] = mapped_column(String(256), nullable=False)

    food_item: Mapped["FoodItem"] = relationship(back_populates="aliases")

    __table_args__ = (
        UniqueConstraint(
            "food_item_id", "locale", "alias",
            name="uq_food_aliases_item_locale_alias",
        ),
        CheckConstraint(
            "locale IN ('ru', 'en', 'pl', 'de')",
            name="ck_food_aliases_locale_supported",
        ),
        # GIN trgm-индекс на alias — в миграции.
    )

    def __repr__(self) -> str:
        return f"<FoodAlias item={self.food_item_id} {self.locale}={self.alias!r}>"


class FoodLog(Base):
    """Immutable журнал съеденного. Partitioned by month (logged_at).

    Не использует ``UUIDPrimaryKeyMixin`` / ``TimestampMixin`` потому что:
        - PK составной (id, logged_at) — Postgres требует партиционный ключ в PK.
        - updated_at не нужен — таблица append-only.
    """

    __tablename__ = "food_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # ON DELETE RESTRICT — каталог не должен удаляться, пока на него ссылаются
    # логи. Если food_item действительно нужно удалить — сначала миграция
    # переписывает food_logs.food_item_id на placeholder.
    food_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("food_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    grams: Mapped[float] = mapped_column(Float, nullable=False)

    # Snapshot нутриентов на момент логирования (см. docstring модуля).
    kcal: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)

    method: Mapped[FoodLogMethod] = mapped_column(food_log_method_enum, nullable=False)
    # Сырая строка пользователя (для текстового ввода) — для отладки и
    # дообучения парсера. NULL для других методов.
    raw_input: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Партиционный ключ. Это «когда я это съел», не «когда залогировал».
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # Составной PK (требование PostgreSQL для partitioned table).
        # Создаётся явно в миграции — здесь дублирование Index() даёт
        # понимание для ORM.
        CheckConstraint(
            "grams > 0 AND grams <= 5000",
            name="ck_food_logs_grams_range",
        ),
        CheckConstraint(
            "kcal >= 0 AND protein_g >= 0 AND fat_g >= 0 AND carbs_g >= 0",
            name="ck_food_logs_nutrients_nonneg",
        ),
        Index("ix_food_logs_user_logged", "user_id", "logged_at"),
        # postgresql_partition_by — Alembic-миграция создаёт партиционное
        # расположение явно через postgresql_partition_by; ORM-side
        # Декларация существует только для autogenerate-сравнения.
        {"postgresql_partition_by": "RANGE (logged_at)"},
    )

    def __repr__(self) -> str:
        return (
            f"<FoodLog user={self.user_id} item={self.food_item_id} "
            f"{self.grams}g at {self.logged_at}>"
        )
