"""Resolve the directory containing vocabulary_final.json.

The vocab data is NOT bundled in the wheel (it is 45MB now and will grow to
~350MB after the scope-C rebuild). Instead it is hosted as a gzipped GitHub
Release asset and downloaded + cached on first use.

Resolution order (see :func:`get_vocab_data_path`):

1. **Env override** — ``PSDL_VOCAB_DATA_DIR``: point at a directory that
   already contains ``vocabulary_final.json``. This is the air-gapped / offline
   / dev escape hatch — when set, NO network access is attempted.
2. **Cache hit** — if ``<cache>/vocabulary_final.json`` already exists, use it.
   The cache dir is ``PSDL_VOCAB_CACHE_DIR`` if set, else
   ``~/.cache/psdl_vocab/<version>``.
3. **Download** — fetch the gzipped asset from the pinned release URL
   (``VOCAB_DATA_URL``), decompress it, and write it into the cache dir
   (atomically, via a temp file + rename so an interrupted download never
   leaves a corrupt ``vocabulary_final.json`` behind). Subsequent loads hit the
   cache (step 2) and never touch the network.

Env vars:
- ``PSDL_VOCAB_DATA_DIR``  — offline override; dir containing the JSON.
- ``PSDL_VOCAB_CACHE_DIR`` — override the download cache location.
"""

import gzip
import os
import shutil
import ssl
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

# Pinned release asset. Bump VOCAB_DATA_VERSION (and the URL tag) when a new
# vocab build is published so caches don't collide across versions.
VOCAB_DATA_VERSION = "v1"
VOCAB_DATA_URL = (
    "https://github.com/Chesterguan/psdl-inspector/releases/download/"
    "vocab-data-v1/vocabulary_final.json.gz"
)

VOCAB_FILENAME = "vocabulary_final.json"


def _cache_dir() -> Path:
    """Directory where the downloaded vocab is cached."""
    override = os.environ.get("PSDL_VOCAB_CACHE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "psdl_vocab" / VOCAB_DATA_VERSION


def _ssl_context() -> ssl.SSLContext:
    """Build an SSL context for the download.

    Prefer certifi's CA bundle when it is importable. This is a soft
    dependency only (psdl_vocab declares no hard deps): certifi ships with
    pip/requests and is present in virtually every environment, and using it
    sidesteps the common macOS python.org "CERTIFICATE_VERIFY_FAILED — unable
    to get local issuer certificate" failure (the system Python ships without a
    populated CA store until ``Install Certificates.command`` is run). When
    certifi is absent we fall back to the platform default context.
    """
    try:
        import certifi  # noqa: PLC0415 — optional, imported lazily

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # pragma: no cover - certifi missing / unusable
        return ssl.create_default_context()


def _download_and_cache(cache_dir: Path) -> None:
    """Download the gzipped vocab, decompress, and write it into cache_dir.

    Writes to a temp file in the same directory then atomically renames into
    place, so an interrupted/failed download never leaves a partial
    vocabulary_final.json that later looks like a valid cache hit.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / VOCAB_FILENAME

    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=".vocab-", suffix=".json.tmp", dir=str(cache_dir)
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)

    try:
        # Stream-download the gz, then decompress straight into the temp file.
        with urllib.request.urlopen(
            VOCAB_DATA_URL, context=_ssl_context()
        ) as resp, gzip.GzipFile(fileobj=resp) as gz, open(tmp_path, "wb") as out:
            shutil.copyfileobj(gz, out)
        # Atomic on POSIX: rename within the same filesystem.
        os.replace(tmp_path, target)
    except (urllib.error.URLError, OSError, EOFError) as exc:
        # Clean up the partial temp file before surfacing the error.
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise RuntimeError(
            "psdl_vocab could not download the vocabulary data from "
            f"{VOCAB_DATA_URL} ({exc}). "
            "For offline/air-gapped installs, set PSDL_VOCAB_DATA_DIR to a "
            "directory containing vocabulary_final.json and retry."
        ) from exc


def get_vocab_data_path() -> Path:
    """Return the directory containing ``vocabulary_final.json``.

    Resolves via env override -> local cache -> first-use download (see module
    docstring). Always returns a real ``pathlib.Path`` directory; the caller
    (VocabularyService) does ``dir / "vocabulary_final.json"``, ``.exists()``,
    and ``open()`` on the result.
    """
    override = os.environ.get("PSDL_VOCAB_DATA_DIR")
    if override:
        p = Path(override)
        if not p.is_dir():
            raise RuntimeError(
                f"PSDL_VOCAB_DATA_DIR={override} is not a directory"
            )
        return p

    cache_dir = _cache_dir()
    if (cache_dir / VOCAB_FILENAME).exists():
        return cache_dir

    _download_and_cache(cache_dir)
    return cache_dir
