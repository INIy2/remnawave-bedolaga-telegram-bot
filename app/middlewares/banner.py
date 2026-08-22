from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.utils.banners import reset_current_banner, resolve_banner_key, set_current_banner


class BannerMiddleware(BaseMiddleware):
    """Определяет раздел апдейта и кладёт его в ContextVar.

    Картинка к экрану цепляется глобальным патчем `Message.answer`/`edit_text`,
    у которого нет доступа к хендлеру, поэтому раздел передаётся через контекст.
    См. `app/utils/banners.py`.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        source: str | None = None
        if isinstance(event, CallbackQuery):
            source = event.data
        elif isinstance(event, Message):
            source = event.text

        token = set_current_banner(resolve_banner_key(source))
        try:
            return await handler(event, data)
        finally:
            reset_current_banner(token)
