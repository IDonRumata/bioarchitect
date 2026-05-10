"""Aiogram-роутеры. Структура: один файл = один логический сценарий."""

from aiogram import Router

from src.bot.handlers import onboarding, start

router = Router(name="main")
router.include_router(start.router)
router.include_router(onboarding.router)

__all__ = ["router"]
