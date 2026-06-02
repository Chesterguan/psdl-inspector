"""Resolve the directory containing the pre-built BioLORD v2 FAISS index.

Resolution order:
1. PSDL_VOCAB_SEARCH_DATA_DIR env var (offline override)
2. Cache hit at PSDL_VOCAB_SEARCH_CACHE_DIR (default ~/.cache/psdl_vocab_search/v2-biolord/)
3. Download tarball from the pinned GitHub Release, unpack atomically into the cache dir.

Required artifact files: index.faiss, index.faiss.meta, metadata.json.
(The slim asset does not include embeddings.npy — only the pre-built FAISS index is shipped.)
"""
from __future__ import annotations

import os
import shutil
import ssl
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

INDEX_VERSION = "v2-biolord"
INDEX_TARBALL_URL = (
    "https://github.com/Chesterguan/psdl-inspector/releases/download/"
    "vocab-embeddings-v2-biolord/vocab-embeddings-v2-biolord.tar.gz"
)
# Slim asset — tarball contains only the three files below (no embeddings.npy).
REQUIRED_FILES = ("index.faiss", "index.faiss.meta", "metadata.json")


def _cache_dir() -> Path:
    """Return the cache directory for the BioLORD v2 index."""
    override = os.environ.get("PSDL_VOCAB_SEARCH_CACHE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "psdl_vocab_search" / INDEX_VERSION


def _all_present(directory: Path) -> bool:
    """Return True if all required files exist in *directory*."""
    return all((directory / f).exists() for f in REQUIRED_FILES)


def _ssl_context() -> ssl.SSLContext:
    """Build an SSL context, preferring certifi's CA bundle when available.

    certifi ships with pip/requests and sidesteps the common macOS python.org
    "CERTIFICATE_VERIFY_FAILED" failure caused by a missing system CA store.
    Falls back to the platform default context if certifi is absent.
    """
    try:
        import certifi  # soft dependency — present in virtually every venv

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # pragma: no cover - certifi missing / unusable
        return ssl.create_default_context()


def _download_and_unpack(cache_dir: Path) -> None:
    """Download the tarball from the pinned GitHub Release and unpack it.

    Uses a temp file + atomic rename strategy so an interrupted download never
    leaves partial/corrupt files that would appear as a valid cache hit on the
    next call.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=".biolord-", suffix=".tar.gz", dir=str(cache_dir)
    )
    os.close(tmp_fd)
    tmp_tarball = Path(tmp_name)

    try:
        print("[psdl_vocab_search] Downloading BioLORD v2 index (~1.7 GB) ...", flush=True)
        with urllib.request.urlopen(
            INDEX_TARBALL_URL, context=_ssl_context()
        ) as resp, open(tmp_tarball, "wb") as out:
            shutil.copyfileobj(resp, out)

        # Unpack into a staging directory, then atomically move each file into
        # place so partial unpacks don't corrupt the cache.
        tmp_unpack = cache_dir / ".unpack_tmp"
        if tmp_unpack.exists():
            shutil.rmtree(tmp_unpack)
        tmp_unpack.mkdir()

        with tarfile.open(tmp_tarball, "r:gz") as tf:
            tf.extractall(str(tmp_unpack))

        # Move only the required files; ignore anything else in the tarball.
        for fname in REQUIRED_FILES:
            src = tmp_unpack / fname
            dst = cache_dir / fname
            if src.exists():
                os.replace(src, dst)

        shutil.rmtree(tmp_unpack, ignore_errors=True)
        print(f"[psdl_vocab_search] Index cached at {cache_dir}", flush=True)

    except (urllib.error.URLError, OSError, EOFError, tarfile.TarError) as exc:
        raise RuntimeError(
            f"psdl_vocab_search could not download the BioLORD v2 index from "
            f"{INDEX_TARBALL_URL} ({exc}). "
            "For offline installs set PSDL_VOCAB_SEARCH_DATA_DIR to a directory "
            "containing the three artifact files (index.faiss, index.faiss.meta, "
            "metadata.json) and retry."
        ) from exc
    finally:
        try:
            tmp_tarball.unlink(missing_ok=True)
        except OSError:
            pass


def get_index_dir() -> Path:
    """Return the directory containing the pre-built BioLORD v2 FAISS index.

    Resolution order (see module docstring):
    1. PSDL_VOCAB_SEARCH_DATA_DIR env override (offline / CI / dev)
    2. Cache hit at the default cache directory
    3. First-use download from the pinned GitHub Release

    Always returns a real :class:`pathlib.Path`; raises :exc:`RuntimeError` on
    misconfiguration or download failure.
    """
    override = os.environ.get("PSDL_VOCAB_SEARCH_DATA_DIR")
    if override:
        p = Path(override)
        if not p.is_dir():
            raise RuntimeError(
                f"PSDL_VOCAB_SEARCH_DATA_DIR={override!r} is not a directory"
            )
        if not _all_present(p):
            missing = [f for f in REQUIRED_FILES if not (p / f).exists()]
            raise RuntimeError(
                f"PSDL_VOCAB_SEARCH_DATA_DIR={override!r} is missing files: {missing}"
            )
        return p

    cache_dir = _cache_dir()
    if _all_present(cache_dir):
        return cache_dir

    _download_and_unpack(cache_dir)
    return cache_dir
