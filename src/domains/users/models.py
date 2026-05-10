"""Модели домена users.

Таблицы:
    - users          — Telegram-аккаунт + локализация + статус.
    - user_profiles  — заполняется через онбординг FSM. ``birth_year`` (не
      полная дата) — GDPR Data Minimization.

Принципы:
    - PK — UUIDv4 (server-generated через uuid_generate_v4 невозможно,
      т. к. extension uuid-ossp не нужен — генерируем на стороне приложения).
    - ``telegram_id`` — BIGINT, индекс уникальный.
    - ``user_profiles`` — 1-к-1 с users.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.domains.users.enums import LifestyleTag, Sex, UserStatus, WorkPattern

if TYPE_CHECKING:
    from src.domains.consent.models import ConsentRecord


# Postgres ENUM-типы. ``create_type=False`` означает, что тип создаём вручную в
# миграции (для идемпотентности и контроля).
user_status_enum = ENUM(
    UserStatus,
    name="user_status",
    values_callable=lambda x: [e.value for e in x],
    create_type=False,
)
sex_enum = ENUM(
    Sex,
    name="sex",
    values_callable=lambda x: [e.value for e in x],
    create_type=False,
)
work_pattern_enum = ENUM(
    WorkPattern,
    name="work_pattern",
    values_callable=lambda x: [e.value for e in x],
    create_type=False,
)


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Аккаунт пользователя. Один Telegram-id = один пользователь."""

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # ISO 3166-1 alpha-2: PL, DE, RU, BY, KZ, ...
    country_iso: Mapped[str | None] = mapped_column(String(2), nullable=True)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="ru")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    status: Mapped[UserStatus] = mapped_column(
        user_status_enum,
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Связи
    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    consents: Mapped[list["ConsentRecord"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "country_iso IS NULL OR length(country_iso) = 2",
            name="country_iso_alpha2",
        ),
        CheckConstraint(
            "locale IN ('ru', 'en', 'pl', 'de')",
            name="locale_supported",
        ),
        Index("ix_users_status_active", "status", postgresql_where="status = 'active'"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id} status={self.status.value}>"


class UserProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Профиль пользователя — заполняется через онбординг.

    GDPR: ``birth_year`` (не полная дата) минимизация ПД.
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    sex: Mapped[Sex] = mapped_column(sex_enum, nullable=False, default=Sex.UNSPECIFIED)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    work_pattern: Mapped[WorkPattern] = mapped_column(
        work_pattern_enum,
        nullable=False,
        default=WorkPattern.UNSPECIFIED,
    )
    lifestyle_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(32)),
        nullable=False,
        default=list,
    )

    user: Mapped["User"] = relationship(back_populates="profile")

    __table_args__ = (
        # Биологические границы. Целевая аудитория 18+; 1900-2008 покрывает с запасом.
        CheckConstraint(
            "birth_year IS NULL OR (birth_year >= 1900 AND birth_year <= 2008)",
            name="birth_year_range",
        ),
        CheckConstraint(
            "height_cm IS NULL OR (height_cm >= 100 AND height_cm <= 250)",
            name="height_cm_range",
        ),
        CheckConstraint(
            "weight_kg IS NULL OR (weight_kg >= 30 AND weight_kg <= 300)",
            name="weight_kg_range",
        ),
    )

    def lifestyle_tags_typed(self) -> list[LifestyleTag]:
        """Тег-лист с приведением к Enum (тихо игнорируя неизвестные)."""
        valid: list[LifestyleTag] = []
        for tag in self.lifestyle_tags:
            try:
                valid.append(LifestyleTag(tag))
            except ValueError:
                continue
        return valid

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id} work={self.work_pattern.value}>"
