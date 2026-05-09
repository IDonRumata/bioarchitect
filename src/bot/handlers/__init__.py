"""Aiogram-роутеры. Структура: один файл = один логический сценарий."""

from aiogram import Router

from src.bot.handlers import start

router = Router(name="main")
router.include_router(start.router)

__all__ = ["router"]
