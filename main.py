from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from core.routes.auth import router as auth_router
from core.routes.conversations import router as conversations_router
from core.routes.requests import router as requests_router
from core.services.application import ApplicationServices
from core.services.db import check_database
from core.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    services = ApplicationServices(get_settings())
    await services.start()
    app.state.services = services
    yield
    await services.stop()


fastapi_app = FastAPI(
    title="Administration Platform Backend",
    description="Backend for the Administration Platform",
    version="0.1.0-development",
    openapi_url="/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

fastapi_app.include_router(requests_router)
fastapi_app.include_router(conversations_router)
fastapi_app.include_router(auth_router)


@fastapi_app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    try:
        check_database()
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from error
    return {"status": "ok"}

fastapi_app.get("/ready", tags=["system"])(health)
fastapi_app.get("/live", tags=["system"])(health)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:fastapi_app",
        host="0.0.0.0",
        port=8765,
        reload=True,
        reload_dirs=["core"],
        log_level="info",
    )

