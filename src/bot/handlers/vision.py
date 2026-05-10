"""Хендлеры логирования еды по фото (Vision Phase 1).

Поток:
    1. Пользователь отправляет фото.
    2. Скачиваем байты → вычисляем pHash → проверяем кэш.
    3. Кэш-промах → VisionParser (Sonnet 4.6) → Phase1Result.
    4. Если нет распознанных продуктов → сообщаем.
    5. Иначе → FSM confirming_item, показываем первый продукт.
    6. ✅ Ок / ✏️ Изменить граммы / ❌ Пропустить → двигаемся по очереди.
    7. На каждый подтверждённый продукт → NutritionService.search →
       авто-лог если best ≥ VISION_LOG_THRESHOLD, иначе «не нашёл».
    8. После очереди → сводка + сброс state.
"""

from __future__ import annotations

import io
import json
from typing import Any, cast

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.vision_phase1 import RecognizedItem, VisionParseError, VisionParser
from src.bot.keyboards.vision import (
    parse_edit_callback,
    parse_ok_callback,
    parse_skip_callback,
    recognition_item_keyboard,
)
from src.bot.states.vision import VisionStates
from src.core.logging import get_logger
from src.domains.nutrition.enums import FoodLogMethod
from src.domains.nutrition.schemas import FoodLogCreate
from src.domains.nutrition.service import NutritionService
from src.domains.users.service import UserService

router = Router(name="vision")
log = get_logger(__name__)

# Порог similarity для авто-логирования после Vision-распознавания.
# Мягче, чем в текстовом вводе (0.85), потому что Vision уже даёт
# нормализованное name_ru.
VISION_LOG_THRESHOLD = 0.5
_TOP_N = 1  # берём только лучший хит (без выбора кандидатов в Phase 1)


@router.message(F.photo)
async def handle_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Любое фото от пользователя."""
    current = await state.get_state()
    if current is not None:
        # Уже в каком-то FSM — игнорируем (например, идёт текстовый ввод).
        return

    assert message.from_user is not None
    assert message.bot is not None

    user_service = UserService(session)
    user, _ = await user_service.get_or_create(
        telegram_id=cast(int, message.from_user.id),
        username=message.from_user.username,
    )
    if user.onboarding_completed_at is None:
        await message.answer("Сначала пройди онбординг — отправь /start.")
        return

    # Берём фото максимального разрешения.
    photo = message.photo[-1]
    buf = io.BytesIO()
    await message.bot.download(photo, destination=buf)
    image_bytes = buf.getvalue()

    await message.answer("🔍 Анализирую фото…")

    parser = VisionParser()
    try:
        result, llm_result = await parser.recognize(
            image_bytes=image_bytes,
            user_id=user.id,
            session=session,
        )
    except VisionParseError as exc:
        log.warning("vision.parse_failed", error=str(exc))
        await message.answer(
            "Не удалось распознать фото. Попробуй сделать снимок чётче "
            "или опиши еду текстом."
        )
        return
    except Exception as exc:  # noqa: BLE001
        log.error("vision.llm_error", error=str(exc))
        await message.answer(
            "Не получилось обратиться к AI. Попробуй ещё раз через минуту."
        )
        return

    if not result.items:
        await message.answer(
            "Не вижу еды на фото. Убедись, что блюдо хорошо освещено "
            "и занимает большую часть кадра."
        )
        return

    cache_note = " <i>(из кэша)</i>" if result.from_cache else ""
    cost_note = ""
    if llm_result is not None:
        cost_note = f" · {llm_result.cost_cents:.2f}¢"

    log.info(
        "vision.recognized",
        items=len(result.items),
        from_cache=result.from_cache,
        cost_cents=llm_result.cost_cents if llm_result else 0,
    )

    # Сохраняем photo_recognitions в БД если не из кэша.
    if llm_result is not None:
        await session.commit()

    await state.set_state(VisionStates.confirming_item)
    await state.update_data(
        vision_items=[item.model_dump() for item in result.items],
        current_vis_idx=0,
        logged=[],
        not_found=[],
        user_locale=user.locale,
    )

    intro = (
        f"Вижу {len(result.items)} продукт(а){cache_note}{cost_note}. "
        "Подтверди каждый:"
    )
    await message.answer(intro)
    await _show_vision_item(message, result.items[0], 0)


@router.callback_query(VisionStates.confirming_item, F.data.startswith("vis:ok:"))
async def on_ok(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    parsed = parse_ok_callback(call.data or "")
    if parsed is None:
        await call.answer("Не понял", show_alert=False)
        return
    idx, grams = parsed

    data = await state.get_data()
    vis_items = list(data.get("vision_items", []))
    if idx != int(data.get("current_vis_idx", -1)) or idx >= len(vis_items):
        await call.answer("Уже неактуально", show_alert=False)
        return

    item = RecognizedItem.model_validate(vis_items[idx])
    await _log_vision_item(call, state, session, data, item, grams, idx)


@router.callback_query(VisionStates.confirming_item, F.data.startswith("vis:edit:"))
async def on_edit(call: CallbackQuery, state: FSMContext) -> None:
    idx = parse_edit_callback(call.data or "")
    if idx is None:
        await call.answer("Не понял", show_alert=False)
        return

    data = await state.get_data()
    if idx != int(data.get("current_vis_idx", -1)):
        await call.answer("Уже неактуально", show_alert=False)
        return

    await state.set_state(VisionStates.entering_grams)
    await state.update_data(editing_vis_idx=idx)

    if call.message is not None:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
    await call.answer()

    if isinstance(call.message, Message):
        await call.message.answer("Введи вес в граммах (например, 180):")


@router.message(VisionStates.entering_grams, F.text)
async def on_grams_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    text = (message.text or "").strip().replace(",", ".")
    try:
        grams = int(float(text))
        if not (1 <= grams <= 5000):
            raise ValueError
    except ValueError:
        await message.answer("Введи число от 1 до 5000, например «200».")
        return

    data = await state.get_data()
    idx = int(data.get("editing_vis_idx", 0))
    vis_items = list(data.get("vision_items", []))

    if idx >= len(vis_items):
        await message.answer("Что-то пошло не так. Попробуй отправить фото заново.")
        await state.clear()
        return

    item = RecognizedItem.model_validate(vis_items[idx])
    await state.set_state(VisionStates.confirming_item)
    await _log_vision_item(message, state, session, data, item, grams, idx)


@router.callback_query(VisionStates.confirming_item, F.data.startswith("vis:skip:"))
async def on_skip(call: CallbackQuery, state: FSMContext) -> None:
    idx = parse_skip_callback(call.data or "")
    if idx is None:
        await call.answer("Не понял", show_alert=False)
        return

    data = await state.get_data()
    vis_items = list(data.get("vision_items", []))
    if idx != int(data.get("current_vis_idx", -1)) or idx >= len(vis_items):
        await call.answer("Уже неактуально", show_alert=False)
        return

    item = RecognizedItem.model_validate(vis_items[idx])
    not_found = list(data.get("not_found", []))
    not_found.append(item.name_ru)

    if call.message is not None:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
    await call.answer()

    await _advance_vision(
        call.message if isinstance(call.message, Message) else None,
        state,
        data | {"not_found": not_found},
        idx,
    )


# ---- Вспомогательные функции ----


async def _log_vision_item(
    trigger: Message | CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    data: dict[str, Any],
    item: RecognizedItem,
    grams: int,
    idx: int,
) -> None:
    """Поиск в каталоге и лог одного подтверждённого Vision-продукта."""
    assert hasattr(trigger, "from_user") and trigger.from_user is not None

    user_service = UserService(session)
    user, _ = await user_service.get_or_create(
        telegram_id=cast(int, trigger.from_user.id),
        username=trigger.from_user.username,
    )

    locale = str(data.get("user_locale") or "ru")
    nutrition = NutritionService(session)

    # Сначала ищем по name_ru в нужной локали, потом по name_en.
    hits = await nutrition.search(
        query=item.name_ru,
        locale=locale,
        limit=_TOP_N,
        min_similarity=VISION_LOG_THRESHOLD,
    )
    if not hits:
        hits = await nutrition.search(
            query=item.name_en,
            locale="en",
            limit=_TOP_N,
            min_similarity=VISION_LOG_THRESHOLD,
        )

    logged = list(data.get("logged", []))
    not_found = list(data.get("not_found", []))

    if hits:
        best = hits[0]
        food_log = await nutrition.log_food(
            FoodLogCreate(
                user_id=user.id,
                food_item_id=best.food_item_id,
                grams=float(grams),
                method=FoodLogMethod.PHOTO_PHASE1,
            )
        )
        await session.commit()
        logged.append(
            {
                "name": best.name,
                "brand": best.brand,
                "grams": grams,
                "kcal": food_log.kcal,
            }
        )
    else:
        not_found.append(f"{item.name_ru} ({grams}г) — нет в каталоге")

    # Убираем клавиатуру у предыдущего сообщения.
    msg: Message | None = None
    if isinstance(trigger, CallbackQuery):
        if call := trigger:
            if call.message is not None:
                try:
                    await call.message.edit_reply_markup(reply_markup=None)
                except TelegramBadRequest:
                    pass
                if isinstance(call.message, Message):
                    msg = call.message
        await trigger.answer()
    else:
        msg = trigger

    await _advance_vision(msg, state, data | {"logged": logged, "not_found": not_found}, idx)


async def _advance_vision(
    message: Message | None,
    state: FSMContext,
    data: dict[str, Any],
    just_done_idx: int,
) -> None:
    next_idx = just_done_idx + 1
    await state.update_data(**(data | {"current_vis_idx": next_idx}))

    vis_items = list(data.get("vision_items", []))
    if next_idx < len(vis_items):
        item = RecognizedItem.model_validate(vis_items[next_idx])
        if message is not None:
            await _show_vision_item(message, item, next_idx)
        return

    # Всё обработано — сводка и сброс.
    await state.clear()
    if message is not None:
        await message.answer(
            _format_summary(
                logged=list(data.get("logged", [])),
                not_found=list(data.get("not_found", [])),
            )
        )


async def _show_vision_item(
    message: Message,
    item: RecognizedItem,
    idx: int,
) -> None:
    confidence_pct = int(item.confidence * 100)
    uncertain_note = " <i>(неуверен)</i>" if item.uncertain else ""
    alts = ""
    if item.alternatives:
        alts = f"\n<i>Возможно: {', '.join(item.alternatives[:2])}</i>"
    text = (
        f"<b>{item.name_ru}</b>{uncertain_note}\n"
        f"Примерно {item.grams_min}–{item.grams_max} г · уверенность {confidence_pct}%"
        f"{alts}"
    )
    await message.answer(text, reply_markup=recognition_item_keyboard(item, idx))


def _format_summary(
    *,
    logged: list[dict[str, Any]],
    not_found: list[str],
) -> str:
    lines: list[str] = []
    if logged:
        total_kcal = sum(item.get("kcal", 0) for item in logged)
        lines.append("<b>Записал по фото:</b>")
        for item in logged:
            label = item["name"]
            if item.get("brand"):
                label = f"{label} ({item['brand']})"
            lines.append(f"• {label} — {item['grams']}г · {round(item['kcal'])} ккал")
        lines.append(f"<b>Итого: {round(total_kcal)} ккал</b>")
    if not_found:
        if lines:
            lines.append("")
        lines.append("<b>Не нашёл в каталоге:</b>")
        for s in not_found:
            lines.append(f"• {s}")
        lines.append("\n<i>Попробуй добавить текстом: «название 200г»</i>")
    if not lines:
        return "Ничего не записал."
    return "\n".join(lines)
