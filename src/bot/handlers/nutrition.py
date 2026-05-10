"""Хендлеры логирования еды (текстовый ввод).

Триггер:
    - Пользователь пишет произвольный текст (после онбординга), который
      Orchestrator классифицирует как ``nutrition_text``.
    - Кнопка «🍽 Еда» из главного меню — подсказка.

Поток:
    1. classify_text → nutrition_text.
    2. NutritionParser (Haiku 4.5) → list[ParsedFoodEntry].
    3. Для каждой entry — NutritionService.search (pg_trgm).
    4. Если best.similarity ≥ AUTO_LOG_THRESHOLD → авто-лог.
    5. Если несколько кандидатов либо лучший < AUTO_LOG_THRESHOLD —
       inline-кнопки выбора (FSM choosing_match).
    6. Если совсем ничего не нашлось — пропускаем entry, в сводке
       помечаем «не нашёл, добавь руками».
    7. По окончании — сводка + сброс state.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.nutrition_parser import NutritionParseError, NutritionParser
from src.agents.orchestrator import IntentType, Orchestrator
from src.bot.keyboards.nutrition import (
    food_choice_keyboard,
    parse_pick_callback,
    parse_skip_callback,
)
from src.bot.states.nutrition import NutritionStates
from src.core.logging import get_logger
from src.domains.nutrition.enums import FoodLogMethod
from src.domains.nutrition.schemas import FoodLogCreate, FoodSearchHit
from src.domains.nutrition.service import NutritionService
from src.domains.users.service import UserService

router = Router(name="nutrition")
log = get_logger(__name__)

# Если лучший кандидат ≥ этого порога — логируем без подтверждения.
AUTO_LOG_THRESHOLD = 0.85
# Для показа кнопок берём кандидатов с similarity ≥ этого порога.
SHOW_THRESHOLD = 0.3
TOP_N_CANDIDATES = 3

_FOOD_MENU_BUTTON = "🍽 Еда"


@router.message(F.text == _FOOD_MENU_BUTTON)
async def food_menu_hint(message: Message) -> None:
    """Кнопка «🍽 Еда» из главного меню — подсказка как логировать."""
    await message.answer(
        "Напиши что съел и сколько, например:\n\n"
        "• <i>куриная грудка 200г, рис 150г</i>\n"
        "• <i>2 яйца и кофе</i>\n"
        "• <i>1 банан</i>\n\n"
        "Я найду продукты в каталоге и посчитаю КБЖУ."
    )


@router.message(F.text, ~F.text.startswith("/"))
async def handle_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Любой не-командный текст. Классификатор решает, наша ли это сцена."""
    # Если уже в FSM — не перехватываем (пусть отрабатывает целевой state).
    current = await state.get_state()
    if current is not None:
        return

    text = (message.text or "").strip()
    if not text:
        return

    intent = Orchestrator().classify_text(text)
    if intent.type != IntentType.NUTRITION_TEXT:
        # Тут сейчас тишина — фоллбек ответ для unknown добавим в спринте 6
        # вместе с RAG/Coach. Пока — только nutrition.
        return

    assert message.from_user is not None
    user_service = UserService(session)
    user, _ = await user_service.get_or_create(
        telegram_id=cast(int, message.from_user.id),
        username=message.from_user.username,
    )
    if user.onboarding_completed_at is None:
        await message.answer("Сначала пройди онбординг — отправь /start.")
        return

    # 1. LLM-парсинг
    parser = NutritionParser()
    try:
        entries, llm_result = await parser.parse(text)
    except NutritionParseError as exc:
        log.warning("nutrition.parse_failed", error=str(exc), text=text)
        await message.answer(
            "Не понял, что и сколько ты съел. Попробуй короче, например "
            "«куриная грудка 200г»."
        )
        return
    except Exception as exc:  # noqa: BLE001 — общий лог наверх
        log.error("nutrition.llm_error", error=str(exc))
        await message.answer(
            "Не получилось обратиться к AI. Попробуй ещё раз через минуту."
        )
        return

    if not entries:
        await message.answer(
            "Не нашёл еды в твоём сообщении. Напиши «что» и «сколько», "
            "например «рис 150г»."
        )
        return

    log.info(
        "nutrition.parsed",
        entries=len(entries),
        cost_cents=llm_result.cost_cents,
        latency_ms=llm_result.latency_ms,
    )

    # 2. Поиск + классификация на «авто-лог» / «спросить»
    nutrition = NutritionService(session)
    locale = user.locale
    pending: list[dict[str, Any]] = []
    logged: list[dict[str, Any]] = []
    not_found: list[str] = []

    for entry in entries:
        hits = await nutrition.search(
            query=entry.query,
            locale=locale,
            limit=TOP_N_CANDIDATES,
            min_similarity=SHOW_THRESHOLD,
        )
        if not hits:
            # Пробуем ещё раз через английский — каталог USDA/manual англ.
            hits = await nutrition.search(
                query=entry.query,
                locale="en",
                limit=TOP_N_CANDIDATES,
                min_similarity=SHOW_THRESHOLD,
            )

        if not hits:
            not_found.append(f"{entry.query} ({entry.grams:g}г)")
            continue

        best = hits[0]
        if best.similarity >= AUTO_LOG_THRESHOLD:
            food_log = await nutrition.log_food(
                FoodLogCreate(
                    user_id=user.id,
                    food_item_id=best.food_item_id,
                    grams=entry.grams,
                    method=FoodLogMethod.TEXT_INPUT,
                    raw_input=text[:512],
                )
            )
            logged.append(_logged_summary(best, entry.grams, food_log.kcal))
        else:
            pending.append(
                {
                    "query": entry.query,
                    "grams": entry.grams,
                    "hits": [_hit_to_dict(h) for h in hits],
                }
            )

    # Зафиксируем авто-логи прежде чем спрашивать про pending.
    await session.commit()

    # 3. Если есть «спросить» — показываем кнопки по первому, остальные — в state.
    if pending:
        await state.set_state(NutritionStates.choosing_match)
        await state.update_data(
            pending=pending,
            logged=logged,
            not_found=not_found,
            current_index=0,
            raw_input=text[:512],
        )
        await _ask_about_entry(message, pending[0], 0)
        return

    # 4. Pending пуст — сразу шлём сводку.
    await message.answer(_format_summary(logged=logged, not_found=not_found))


@router.callback_query(NutritionStates.choosing_match, F.data.startswith("nut:pick:"))
async def on_pick(
    call: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    parsed = parse_pick_callback(call.data or "")
    if parsed is None:
        await call.answer("Не понял выбор", show_alert=False)
        return
    idx, food_item_id, grams = parsed

    data = await state.get_data()
    pending = list(data.get("pending", []))
    if idx != int(data.get("current_index", -1)) or idx >= len(pending):
        await call.answer("Этот выбор уже неактуален", show_alert=False)
        return

    assert call.from_user is not None
    user_service = UserService(session)
    user, _ = await user_service.get_or_create(
        telegram_id=cast(int, call.from_user.id),
        username=call.from_user.username,
    )

    nutrition = NutritionService(session)
    food_log = await nutrition.log_food(
        FoodLogCreate(
            user_id=user.id,
            food_item_id=food_item_id,
            grams=grams,
            method=FoodLogMethod.TEXT_INPUT,
            raw_input=str(data.get("raw_input") or "")[:512],
        )
    )
    await session.commit()

    chosen = next(
        (h for h in pending[idx]["hits"] if UUID(h["food_item_id"]) == food_item_id),
        None,
    )
    logged = list(data.get("logged", []))
    if chosen is not None:
        logged.append(
            {
                "name": chosen["name"],
                "brand": chosen.get("brand"),
                "grams": grams,
                "kcal": food_log.kcal,
            }
        )

    await _advance(call, state, data | {"logged": logged}, idx)


@router.callback_query(NutritionStates.choosing_match, F.data.startswith("nut:skip:"))
async def on_skip(call: CallbackQuery, state: FSMContext) -> None:
    idx = parse_skip_callback(call.data or "")
    if idx is None:
        await call.answer("Не понял", show_alert=False)
        return
    data = await state.get_data()
    pending = list(data.get("pending", []))
    if idx != int(data.get("current_index", -1)) or idx >= len(pending):
        await call.answer("Уже неактуально", show_alert=False)
        return

    not_found = list(data.get("not_found", []))
    not_found.append(f"{pending[idx]['query']} ({pending[idx]['grams']:g}г)")
    await _advance(call, state, data | {"not_found": not_found}, idx)


async def _advance(
    call: CallbackQuery,
    state: FSMContext,
    data: dict[str, Any],
    just_done_index: int,
) -> None:
    """Перейти к следующему pending или завершить сводкой."""
    pending = list(data.get("pending", []))
    next_index = just_done_index + 1
    await state.update_data(**(data | {"current_index": next_index}))

    # Снимаем клавиатуру у предыдущего вопроса.
    if call.message is not None:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
    await call.answer()

    if next_index < len(pending):
        if isinstance(call.message, Message):
            await _ask_about_entry(call.message, pending[next_index], next_index)
        return

    # Все обработали — сводка и сброс.
    await state.clear()
    if isinstance(call.message, Message):
        await call.message.answer(
            _format_summary(
                logged=list(data.get("logged", [])),
                not_found=list(data.get("not_found", [])),
            )
        )


async def _ask_about_entry(
    message: Message,
    pending_entry: dict[str, Any],
    entry_index: int,
) -> None:
    hits = [_dict_to_hit(h) for h in pending_entry["hits"]]
    grams = float(pending_entry["grams"])
    text = (
        f"Что такое <b>«{pending_entry['query']}»</b> "
        f"({grams:g}г)?\nВыбери из каталога:"
    )
    await message.answer(
        text,
        reply_markup=food_choice_keyboard(hits, grams=grams, entry_index=entry_index),
    )


# ---- Сериализация для FSM (UUID/Enum → str) ----


def _hit_to_dict(hit: FoodSearchHit) -> dict[str, Any]:
    return {
        "food_item_id": str(hit.food_item_id),
        "name": hit.name,
        "brand": hit.brand,
        "source": hit.source.value,
        "verified": hit.verified,
        "kcal_100g": hit.kcal_100g,
        "protein_100g": hit.protein_100g,
        "fat_100g": hit.fat_100g,
        "carbs_100g": hit.carbs_100g,
        "similarity": hit.similarity,
    }


def _dict_to_hit(raw: dict[str, Any]) -> FoodSearchHit:
    return FoodSearchHit.model_validate(raw)


def _logged_summary(
    hit: FoodSearchHit,
    grams: float,
    kcal: float,
) -> dict[str, Any]:
    return {
        "name": hit.name,
        "brand": hit.brand,
        "grams": grams,
        "kcal": kcal,
    }


def _format_summary(
    *,
    logged: list[dict[str, Any]],
    not_found: list[str],
) -> str:
    lines: list[str] = []
    if logged:
        total_kcal = sum(item.get("kcal", 0) for item in logged)
        lines.append("<b>Записал:</b>")
        for item in logged:
            label = item["name"]
            if item.get("brand"):
                label = f"{label} ({item['brand']})"
            lines.append(f"• {label} — {item['grams']:g}г · {round(item['kcal'])} ккал")
        lines.append(f"<b>Итого: {round(total_kcal)} ккал</b>")
    if not_found:
        if lines:
            lines.append("")
        lines.append("<b>Не нашёл в каталоге:</b>")
        for s in not_found:
            lines.append(f"• {s}")
        lines.append(
            "\n<i>Если что-то важное — напиши коротким названием, "
            "например «рис» вместо «бурый рис басмати».</i>"
        )
    if not lines:
        return "Ничего не записал."
    return "\n".join(lines)
