"""Request-scoped identity made available to synchronous LangChain tools."""
from __future__ import annotations

from contextvars import ContextVar, Token


_current_user_id: ContextVar[str | None] = ContextVar("liquidround_user_id", default=None)


def current_user_id() -> str | None:
    return _current_user_id.get()


def set_current_user_id(user_id: str | None) -> Token:
    return _current_user_id.set(str(user_id) if user_id else None)


def reset_current_user_id(token: Token) -> None:
    _current_user_id.reset(token)
