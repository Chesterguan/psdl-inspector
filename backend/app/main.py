"""FastAPI application entry point."""

from dotenv import load_dotenv
load_dotenv()  # Load .env file before other imports

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from importlib.metadata import version as pkg_version

from app.routers import validate, outline, export, generate

# Get psdl-lang version
try:
    PSDL_LANG_VERSION = pkg_version("psdl-lang")
except Exception:
    PSDL_LANG_VERSION = "unknown"

INSPECTOR_VERSION = "0.1.0"

app = FastAPI(
    title="PSDL Inspector API",
    description="API for validating, analyzing, and exporting PSDL scenarios",
    version=INSPECTOR_VERSION,
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
app.include_router(generate.router, prefix="/api", tags=["generate"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "psdl-inspector-api",
        "version": INSPECTOR_VERSION,
        "psdl_lang_version": PSDL_LANG_VERSION,
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/version")
async def get_version():
    """Get version information."""
    return {
        "inspector": INSPECTOR_VERSION,
        "psdl_lang": PSDL_LANG_VERSION,
    }
