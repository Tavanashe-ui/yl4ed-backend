from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.audit import current_ip, current_user_agent

class AuditContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Set IP and user-agent from the request
        current_ip.set(request.client.host if request.client else None)
        current_user_agent.set(request.headers.get("user-agent"))
        
        response = await call_next(request)
        return response