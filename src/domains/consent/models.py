"""Модели домена consent — GDPR-согласия (append-only).

Принципы:
    - **Никогда не UPDATE.** Только INSERT новых строк. Отзыв = новая запись
      с ``revoked=true`` и ссылкой на исходную через ``superseded_by``.
    - ``version`` — версия документа согласия (как только в TOS меняется
      health-clause, бампается версия и старые согласия становятся
      устаревшими, требуется пере-сбор).
    - ``ip_hash`` — sha256(ip + salt) на момент согласия. Полный IP не
      хранится (GDPR Data Minimization).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.base import Base, UUIDPrimaryKeyMixin
from src.domains.consent.enums import ConsentType

if TYPE_CHECKING:
    from src.domains.users.models import User


consent_type_enum = ENUM(
    ConsentType,
    name="consent_type",
    values_callable=lambda x: [e.value for e in x],
    create_type=False,
)


class ConsentRecord(Base, UUIDPrimaryKeyMixin):
    """Append-only запись согласия / отзыва согласия.

    Чтобы получить актуальный статус согласия — выбрать последнюю запись по
    (user_id, consent_type, version) и проверить ``granted``.
    """

    __tablename__ = "consent_records"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_type: Mapped[ConsentType] = mapped_column(consent_type_enum, nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship(back_populates="consents")

    __table_args__ = (
        Index(
            "ix_consent_records_user_type_time",
            "user_id",
            "consent_type",
            "granted_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ConsentRecord user={self.user_id} type={self.consent_type.value} "
            f"v={self.version} granted={self.granted}>"
        )
