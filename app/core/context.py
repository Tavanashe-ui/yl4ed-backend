from contextvars import ContextVar
from typing import Optional

current_user_id: ContextVar[Optional[int]] = ContextVar('current_user_id', default=None)
current_username: ContextVar[Optional[str]] = ContextVar('current_username', default=None)
current_ip: ContextVar[Optional[str]] = ContextVar('current_ip', default=None)
current_user_agent: ContextVar[Optional[str]] = ContextVar('current_user_agent', default=None)