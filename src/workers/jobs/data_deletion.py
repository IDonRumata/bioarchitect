"""ARQ-задача: hard-delete пользователей после 30-дневного grace period.

Запускается ежедневно через ARQ cron (см. ``WorkerSettings.cron_jobs``).
GDPR Art. 17 — право на удаление.

Логика:
    1. Найти всех пользователей с status='pending_deletion' и
       deletion_requested_at < now() - GDPR_DELETION_GRACE_DAYS дней.
    2. DELETE FROM users WHERE id = ?  — каскадно удаляет user_profiles,
       consent_records, food_logs, lab_*, и т.д. (все FK с ON DELETE CASCADE).
    3. Логируем количество удалённых аккаунтов в Sentry / Prometheus.

Идемпотентно: повторный запуск в тот же день ничего не сломает.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select

from src.core.config import get_settings
from src.core.db.session import get_sessionmaker
from src.core.logging import get_logger
from src.domains.users.enums import UserStatus
from src.domains.users.models import User

log = get_logger(__name__)


async def data_deletion_processor(ctx: dict[str, Any]) -> dict[str, int]:
    """Ежедневный воркер hard-delete просроченных аккаунтов.

    Returns:
        Сводка для логов: ``{"deleted": N, "scanned": M}``.
    """
    settings = get_settings()
    grace_days = settings.gdpr_deletion_grace_days
    cutoff = datetime.now(UTC) - timedelta(days=grace_days)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        # Сначала список — для логирования и аудита
        stmt = select(User.id, User.telegram_id).where(
            User.status == UserStatus.PENDING_DELETION,
            User.deletion_requested_at.is_not(None),
            User.deletion_requested_at < cutoff,
        )
        result = await session.execute(stmt)
        rows = result.all()
        count = len(rows)

        if count == 0:
            log.info("data_deletion.no_eligible_users", grace_days=grace_days)
            return {"deleted": 0, "scanned": 0}

        for user_id, tg_id in rows:
            log.warning(
                "data_deletion.hard_delete",
                user_id=str(user_id),
                telegram_id=tg_id,
                grace_days=grace_days,
            )

        # Cascade-delete по PK
        ids = [row[0] for row in rows]
        await session.execute(delete(User).where(User.id.in_(ids)))
        await session.commit()

        log.info("data_deletion.completed", deleted=count)
        return {"deleted": count, "scanned": count}
