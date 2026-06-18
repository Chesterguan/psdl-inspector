FROM python:3.11-slim

WORKDIR /app

# Keep the HuggingFace cache inside /app so the model baked in at build time
# (below) is found by the runtime user at the same path.
ENV HF_HOME=/app/.hf_cache

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# BioLORD v2 anchoring/search needs the ML stack (the psdl_vocab_search [ml]
# extra) + the query-embedder model — none of which are in requirements.txt, so
# without this the container silently falls back to the slow legacy engine.
# Install CPU-only torch (much smaller than the default CUDA build) + the ML libs,
# then bake the model into the image so runtime query embedding is instant
# (no first-use HuggingFace download).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir sentence-transformers faiss-cpu
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('FremyCompany/BioLORD-2023')"

# Copy application code
COPY . .

# Create non-root user. Pre-create the BioLORD v2 index cache dir owned by
# appuser so the mounted named volume (docker-compose) inherits that ownership —
# otherwise the volume mounts root-owned and appuser can't write the index.
RUN useradd -m appuser \
 && mkdir -p /home/appuser/.cache/psdl_vocab_search \
 && chown -R appuser:appuser /app /home/appuser/.cache
USER appuser

EXPOSE 8200

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]
