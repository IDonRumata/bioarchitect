"""Aiogram-роутеры. Структура: один файл = один логический сценарий."""

from aiogram import Router

from src.bot.handlers import deletion, nutrition, onboarding, profile, settings, start, vision

router = Router(name="main")
router.include_router(start.router)
router.include_router(onboarding.router)
router.include_router(profile.router)
router.include_router(settings.router)
router.include_router(deletion.router)
# vision — перед nutrition: обрабатывает F.photo до общего text catch-all.
router.include_router(vision.router)
# nutrition — последний: общий catch-all для не-командных текстов.
router.include_router(nutrition.router)

__all__ = ["router"]
