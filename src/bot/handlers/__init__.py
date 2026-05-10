"""Aiogram-роутеры. Структура: один файл = один логический сценарий."""

from aiogram import Router

from src.bot.handlers import deletion, onboarding, profile, settings, start

router = Router(name="main")
router.include_router(start.router)
router.include_router(onboarding.router)
router.include_router(profile.router)
router.include_router(settings.router)
router.include_router(deletion.router)

__all__ = ["router"]
