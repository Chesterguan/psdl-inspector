"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import validate, outline, export

app = FastAPI(
    title="PSDL Inspector API",
    description="API for validating, analyzing, and exporting PSDL scenarios",
    version="0.1.0",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9806"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(validate.router, prefix="/api", tags=["validation"])
app.include_router(outline.router, prefix="/api", tags=["outline"])
app.include_router(export.router, prefix="/api", tags=["export"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "psdl-inspector-api", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
