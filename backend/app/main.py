from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_TITLE, APP_DESCRIPTION, APP_VERSION
from app.api.routes_repository import router as repository_router
from app.api.routes_github import router as github_router
from app.api.routes_scan import router as scan_router
from app.api.routes_findings import router as findings_router
from app.api.routes_impact import router as impact_router

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular route handlers
app.include_router(repository_router)
app.include_router(github_router)
app.include_router(scan_router)
app.include_router(findings_router)
app.include_router(impact_router)


@app.get("/")
def root():
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "status": "online",
        "endpoints": {
            "health": "/health",
            "scan": "/repository/scan",
            "repositories": "/repositories",
            "findings": "/findings/{repository_id}",
            "impact": "/impact/{repository_id}",
            "docs": "/docs",
        },
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": APP_VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
