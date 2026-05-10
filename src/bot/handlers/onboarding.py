"""Хендлер онбординга — FSM из 8 шагов (GDPR + 5 этапов из ТЗ §5.1)."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.onboarding import (
    countries_keyboard,
    gdpr_consent_keyboard,
    lifestyle_tags_keyboard,
    sex_keyboard,
    work_pattern_keyboard,
)
from src.bot.states.onboarding import OnboardingStates
from src.core.logging import get_logger
from src.domains.consent.enums import ConsentType
from src.domains.consent.service import ConsentService
from src.domains.users.enums import LifestyleTag, Sex, WorkPattern
from src.domains.users.schemas import OnboardingPayload
from src.domains.users.service import OnboardingError, UserService

log = get_logger(__name__)
router = Router(name="onboarding")


# ---------- Точка входа: запускается из /start handler'а ----------

async def begin_onboarding(message: Message, state: FSMContext) -> None:
    """Показать GDPR-согласие. Вызывается из start.py."""
    await state.set_state(OnboardingStates.awaiting_gdpr_consent)
    await message.answer(
        "<b>Перед тем как начать — пара слов о приватности.</b>\n\n"
        "BioArchitect — wellness-сервис. Чтобы помогать тебе с питанием и "
        "самочувствием, мне нужно обрабатывать данные о твоём здоровье "
        "(вес, давление, питание, лабораторные значения).\n\n"
        "По GDPR Art. 9 — это особая категория данных, и нужно твоё "
        "явное согласие.\n\n"
        "🇪🇺 Данные хранятся <b>только на серверах в EU</b>.\n"
        "🗑 Удаление одной кнопкой — в любой момент.\n"
        "🔐 Фото еды не сохраняем (только хеш для кэша).\n"
        "🔒 Фото бланков анализов — зашифрованы.\n\n"
        "Согласен на обработку health-данных?",
        reply_markup=gdpr_consent_keyboard(),
    )


# ---------- Шаг 0: GDPR ----------

@router.callback_query(
    OnboardingStates.awaiting_gdpr_consent,
    F.data.startswith("onboard:gdpr:"),
)
async def on_gdpr(
    cq: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    assert cq.data is not None
    assert cq.message is not None
    decision = cq.data.split(":", 2)[2]

    if decision != "agree":
        await cq.message.edit_text(
            "Без этого согласия я не смогу хранить твои данные. "
            "Если передумаешь — нажми /start ещё раз."
        )
        await state.clear()
        await cq.answer()
        return

    user_service = UserService(session)
    consent_service = ConsentService(session)

    user, _ = await user_service.get_or_create(
        telegram_id=cast(int, cq.from_user.id),
        username=cq.from_user.username,
    )
    await consent_service.grant(
        user_id=user.id,
        consent_type=ConsentType.HEALTH_DATA_PROCESSING,
        notes="Granted via Telegram onboarding FSM",
    )
    await consent_service.grant(
        user_id=user.id,
        consent_type=ConsentType.TERMS_OF_SERVICE,
        notes="Granted via Telegram onboarding FSM",
    )
    log.info("onboarding.consent_granted", user_id=str(user.id))

    await state.set_state(OnboardingStates.awaiting_country)
    await state.update_data(user_db_id=str(user.id))
    await cq.message.edit_text(
        "Спасибо! 🙏\n\n<b>Шаг 1/5.</b> В какой стране ты живёшь?\n"
        "Это нужно, чтобы подобрать референсы лабораторных значений и базу "
        "заправок.",
        reply_markup=countries_keyboard(),
    )
    await cq.answer()


# ---------- Шаг 1: страна ----------

@router.callback_query(
    OnboardingStates.awaiting_country,
    F.data.startswith("onboard:country:"),
)
async def on_country(cq: CallbackQuery, state: FSMContext) -> None:
    assert cq.data is not None
    assert cq.message is not None
    code = cq.data.split(":", 2)[2]

    if code == "other":
        await cq.message.edit_text(
            "Напиши двухбуквенный код страны (например: ES, IT, FR)."
        )
        await cq.answer()
        return

    await state.update_data(country_iso=code)
    await state.set_state(OnboardingStates.awaiting_sex)
    await cq.message.edit_text(
        "<b>Шаг 2/5.</b> Биологический пол.\n"
        "Это нужно для интерпретации лабораторных референсов "
        "(они отличаются для М и Ж).",
        reply_markup=sex_keyboard(),
    )
    await cq.answer()


@router.message(OnboardingStates.awaiting_country, F.text.regexp(r"^[A-Za-z]{2}$"))
async def on_country_text(message: Message, state: FSMContext) -> None:
    assert message.text is not None
    code = message.text.strip().upper()
    await state.update_data(country_iso=code)
    await state.set_state(OnboardingStates.awaiting_sex)
    await message.answer(
        "<b>Шаг 2/5.</b> Биологический пол.\n"
        "Это нужно для интерпретации лабораторных референсов "
        "(они отличаются для М и Ж).",
        reply_markup=sex_keyboard(),
    )


@router.message(OnboardingStates.awaiting_country)
async def on_country_invalid(message: Message) -> None:
    await message.answer("Нужен двухбуквенный код страны (например: ES). Попробуй ещё раз.")


# ---------- Шаг 2: пол ----------

@router.callback_query(
    OnboardingStates.awaiting_sex,
    F.data.startswith("onboard:sex:"),
)
async def on_sex(cq: CallbackQuery, state: FSMContext) -> None:
    assert cq.data is not None
    assert cq.message is not None
    sex_value = cq.data.split(":", 2)[2]
    await state.update_data(sex=sex_value)
    await state.set_state(OnboardingStates.awaiting_birth_year)
    await cq.message.edit_text(
        "<b>Шаг 2/5</b> (продолжение). В каком году ты родился(ась)?\n"
        "Просто число, например: <code>1985</code>.\n\n"
        "<i>Полную дату не запрашиваю — это GDPR Data Minimization.</i>"
    )
    await cq.answer()


@router.message(OnboardingStates.awaiting_birth_year, F.text.regexp(r"^\d{4}$"))
async def on_birth_year(message: Message, state: FSMContext) -> None:
    assert message.text is not None
    year = int(message.text.strip())
    current_year = datetime.now().year
    # 18+ обязательно (Censor blocklist)
    if year < 1900 or year > current_year - 18:
        await message.answer(
            f"Год рождения должен быть от 1900 до {current_year - 18} "
            f"(только совершеннолетние). Попробуй ещё раз."
        )
        return
    await state.update_data(birth_year=year)
    await state.set_state(OnboardingStates.awaiting_height)
    await message.answer(
        "<b>Шаг 3/5.</b> Какой у тебя рост в сантиметрах?\n"
        "Например: <code>178</code>"
    )


@router.message(OnboardingStates.awaiting_birth_year)
async def on_birth_year_invalid(message: Message) -> None:
    await message.answer("Нужно 4-значное число года, например: 1985.")


# ---------- Шаг 3: рост и вес ----------

@router.message(OnboardingStates.awaiting_height, F.text.regexp(r"^\d{2,3}$"))
async def on_height(message: Message, state: FSMContext) -> None:
    assert message.text is not None
    height = int(message.text.strip())
    if height < 100 or height > 250:
        await message.answer("Рост должен быть от 100 до 250 см. Попробуй ещё раз.")
        return
    await state.update_data(height_cm=height)
    await state.set_state(OnboardingStates.awaiting_weight)
    await message.answer(
        "<b>Шаг 3/5</b> (продолжение). А вес в килограммах?\n"
        "Например: <code>82</code> или <code>82.5</code>"
    )


@router.message(OnboardingStates.awaiting_height)
async def on_height_invalid(message: Message) -> None:
    await message.answer("Нужно число от 100 до 250.")


@router.message(OnboardingStates.awaiting_weight, F.text.regexp(r"^\d{2,3}([.,]\d{1,2})?$"))
async def on_weight(message: Message, state: FSMContext) -> None:
    assert message.text is not None
    raw = message.text.strip().replace(",", ".")
    weight = float(raw)
    if weight < 30 or weight > 300:
        await message.answer("Вес должен быть от 30 до 300 кг. Попробуй ещё раз.")
        return
    await state.update_data(weight_kg=weight)
    await state.set_state(OnboardingStates.awaiting_work_pattern)
    await message.answer(
        "<b>Шаг 4/5.</b> Какой у тебя график работы?",
        reply_markup=work_pattern_keyboard(),
    )


@router.message(OnboardingStates.awaiting_weight)
async def on_weight_invalid(message: Message) -> None:
    await message.answer("Нужно число от 30 до 300, можно с десятичной точкой (82.5).")


# ---------- Шаг 4: тип работы ----------

@router.callback_query(
    OnboardingStates.awaiting_work_pattern,
    F.data.startswith("onboard:work:"),
)
async def on_work(cq: CallbackQuery, state: FSMContext) -> None:
    assert cq.data is not None
    assert cq.message is not None
    work_value = cq.data.split(":", 2)[2]
    await state.update_data(work_pattern=work_value, lifestyle_tags=[])
    await state.set_state(OnboardingStates.awaiting_lifestyle_tags)
    await cq.message.edit_text(
        "<b>Шаг 5/5.</b> Что из этого про тебя?\n"
        "Можно выбрать несколько или пропустить.\n\n"
        "<i>Это <b>не</b> диагнозы, просто привычки питания и контекст. "
        "Помогает мне адаптировать рекомендации.</i>",
        reply_markup=lifestyle_tags_keyboard(set()),
    )
    await cq.answer()


# ---------- Шаг 5: lifestyle-теги ----------

@router.callback_query(
    OnboardingStates.awaiting_lifestyle_tags,
    F.data.startswith("onboard:tag:"),
)
async def on_tag_toggle(cq: CallbackQuery, state: FSMContext) -> None:
    assert cq.data is not None
    assert cq.message is not None
    tag = cq.data.split(":", 2)[2]
    data = await state.get_data()
    selected = set(data.get("lifestyle_tags") or [])
    if tag in selected:
        selected.remove(tag)
    else:
        selected.add(tag)
    await state.update_data(lifestyle_tags=list(selected))
    await cq.message.edit_reply_markup(reply_markup=lifestyle_tags_keyboard(selected))
    await cq.answer()


@router.callback_query(
    OnboardingStates.awaiting_lifestyle_tags,
    F.data.in_({"onboard:tags:done", "onboard:tags:skip"}),
)
async def on_tags_done(
    cq: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    assert cq.data is not None
    assert cq.message is not None

    data = await state.get_data()
    tags_raw: list[str] = data.get("lifestyle_tags") or []

    # Валидируем теги через Enum (фильтруем неизвестные)
    valid_tags: list[LifestyleTag] = []
    for t in tags_raw:
        try:
            valid_tags.append(LifestyleTag(t))
        except ValueError:
            continue

    payload = OnboardingPayload(
        country_iso=data["country_iso"],
        locale="ru",  # TODO sprint-2: locale picker
        sex=Sex(data["sex"]),
        birth_year=int(data["birth_year"]),
        height_cm=int(data["height_cm"]),
        weight_kg=float(data["weight_kg"]),
        work_pattern=WorkPattern(data["work_pattern"]),
        lifestyle_tags=valid_tags,
    )

    user_service = UserService(session)
    user, _ = await user_service.get_or_create(
        telegram_id=cast(int, cq.from_user.id),
        username=cq.from_user.username,
    )
    try:
        await user_service.complete_onboarding(user=user, payload=payload)
    except OnboardingError as exc:
        log.error("onboarding.failed", error=str(exc), user_id=str(user.id))
        await cq.message.edit_text(
            "Что-то пошло не так. Попробуй заново через /start."
        )
        await state.clear()
        await cq.answer()
        return

    await state.clear()
    log.info("onboarding.completed", user_id=str(user.id))
    await cq.message.edit_text(
        "🎉 <b>Готово!</b>\n\n"
        "Я знаю про тебя главное. Дальше — основные команды:\n\n"
        "🍽 <b>/food</b> или просто фото еды — записать приём пищи\n"
        "⏱ <b>/fast</b> — интервальное голодание\n"
        "💚 <b>/checkin</b> — ежедневный замер\n"
        "📊 <b>/today</b> — итоги дня\n"
        "❓ <b>/help</b> — все команды\n\n"
        "<i>Помни: я wellness-помощник, а не врач. По вопросам здоровья — "
        "к врачу.</i>"
    )
    await cq.answer()
