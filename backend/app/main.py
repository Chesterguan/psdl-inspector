"""FastAPI application entry point."""

from dotenv import load_dotenv
load_dotenv()  # Load .env file before other imports

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from importlib.metadata import version as pkg_version

from app.routers import validate, outline, export, generate, vocabulary, meds

# Get psdl-lang version
try:
    PSDL_LANG_VERSION = pkg_version("psdl-lang")
except Exception:
    PSDL_LANG_VERSION = "unknown"

INSPECTOR_VERSION = "0.2.0"

app = FastAPI(
    title="PSDL Inspector API",
    description="API for validating, analyzing, and exporting PSDL scenarios",
    version=INSPECTOR_VERSION,
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9806", "http://localhost:9900", "http://localhost:8300"],  # Next.js + prototype
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(validate.router, prefix="/api", tags=["validation"])
app.include_router(outline.router, prefix="/api", tags=["outline"])
app.include_router(export.router, prefix="/api", tags=["export"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(vocabulary.router, prefix="/api", tags=["vocabulary"])
app.include_router(meds.router, prefix="/api", tags=["meds"])


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
