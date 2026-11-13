from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.catalog import router as catalog_router
from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.db.repository import SessionNotFound, SubtaskMismatch, SubtaskNotFound, TaskNotFound


def create_app() -> FastAPI:
    app = FastAPI(title="Pomodoro Attention API")
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(catalog_router)

    @app.exception_handler(SessionNotFound)
    @app.exception_handler(TaskNotFound)
    @app.exception_handler(SubtaskNotFound)
    async def not_found(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(SubtaskMismatch)
    async def subtask_mismatch(_request: Request, exc: SubtaskMismatch) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    return app
