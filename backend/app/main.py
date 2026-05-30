from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_documents import router as documents_router
from app.api.routes_entities import router as entities_router
from app.api.routes_graph import router as graph_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_search import router as search_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
    app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(search_router, prefix="/api/search", tags=["search"])
    app.include_router(entities_router, prefix="/api/entities", tags=["entities"])
    app.include_router(graph_router, prefix="/api/graph", tags=["graph"])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

