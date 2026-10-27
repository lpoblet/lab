from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.db.repository import SessionNotFound
from app.domain.session import InvalidSessionTransition


def create_app() -> FastAPI:
    app = FastAPI(title="Pomodoro Attention API")
    app.include_router(health_router)
    app.include_router(sessions_router)

    @app.exception_handler(SessionNotFound)
    async def session_not_found(_request: Request, exc: SessionNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidSessionTransition)
    async def invalid_transition(_request: Request, exc: InvalidSessionTransition) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

    return app
