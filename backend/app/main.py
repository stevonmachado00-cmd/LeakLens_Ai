from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.middleware.logging import LoggingMiddleware
from app.api.v1.api import api_router

from app.middleware.errors import global_exception_handler

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Set all CORS enabled origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom Logging Middleware
    application.add_middleware(LoggingMiddleware)

    # Global Exception Handler
    application.add_exception_handler(Exception, global_exception_handler)

    application.include_router(api_router, prefix=settings.API_V1_STR)

    @application.get("/health")
    async def health_check():
        return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION}

    return application

app = get_application()
