# Deployment Guide


PSDL Inspector can be deployed in two ways:

1. **Live Demo** - Hosted service for quick testing
2. **Self-Hosted** - Docker Compose for local/private deployment

## Live Demo (Vercel + Render)

The live demo is deployed from the `production` branch only. Pushing to `main` does NOT trigger deployment.

### Deployment Workflow

```
main (development) ──────────────────────────►
                          │
                          │ merge when ready
                          ▼
production (deploys) ────────────────────────►
```

### Initial Setup

#### 1. Create `production` branch

```bash
git checkout -b production
git push -u origin production
```

#### 2. Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and import your repository
2. Configure:
   - **Framework**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Production Branch**: `production` (not main)
3. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL (add after backend deploy)

#### 3. Deploy Backend to Render

1. Go to [render.com](https://render.com) and create new Web Service
2. Connect your repository
3. Configure:
   - **Branch**: `production`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free (or Starter for better performance)
4. No environment variables needed (users provide their own API keys in the UI)

#### 4. Update Vercel with Backend URL

After Render deploys, copy the backend URL (e.g., `https://psdl-inspector-api.onrender.com`) and add it to Vercel's environment variables.

### Deploying Updates

```bash
# Work on main branch
git checkout main
git add . && git commit -m "feat: new feature"
git push origin main

# When ready to deploy
git checkout production
git merge main
git push origin production  # This triggers deployment
```

### Alternative: One-Click Render Deploy

Use the `render.yaml` blueprint for automatic setup:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

---

## Self-Hosted (Docker Compose)

Run PSDL Inspector on your own machine or server.

### Prerequisites

- Docker and Docker Compose installed
- (Optional) OpenAI API key for AI generation
- (Optional) Ollama for local LLM

### Quick Start

```bash
# Clone the repository
git clone https://github.com/Chesterguan/psdl-inspector.git
cd psdl-inspector

# (Optional) Configure environment
cp .env.example .env
# Edit .env with your settings

# Start services
docker-compose up -d

# Access the app
open http://localhost:9806
```

### With Ollama (Local LLM)

If you want to use local LLMs instead of OpenAI:

```bash
# Install Ollama first
brew install ollama  # macOS
# or see https://ollama.ai for other platforms

# Start Ollama and pull a model
ollama serve &
ollama pull mistral-small

# Then start PSDL Inspector
docker-compose up -d
```

The app will detect Ollama automatically.

### Docker Services

| Service | Port | Image Size | Description |
|---------|------|------------|-------------|
| `frontend` | 9806 | ~200MB | Next.js web interface |
| `backend` | 8200 | ~5.3GB | FastAPI REST API + OMOP vocabulary + BioLORD anchoring stack |

**Note**: The backend image is large because it bundles the OMOP vocabulary (~1GB) plus the BioLORD anchoring stack (CPU torch + the embedder model). On the first anchor it downloads the ~1.7GB BioLORD v2 index once into the `vocab_cache` volume. Set `ANCHORING_ENGINE=` (empty) to use the lighter legacy engine instead (no 1.7GB download).

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key for AI generation (optional) |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama server URL |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8200` | Backend API URL (frontend) |
| `ANCHORING_ENGINE` | `biolord_v2` | Anchoring engine; set empty for the lighter legacy engine. See [Using Inspector](usage.md) |
| `GENERATE_SKIP_ENRICHMENT` | `1` | Skip generation-time vocab enrichment (anchoring still runs at export) |
| `PREFLIGHT_DB_URL` | - | Postgres URL to enable the live `EXPLAIN` preflight (metadata only) |
| `OBSERVATORY_CATALOG_DIR` | - | Path to a generated Observatory `catalog.json` for the Data Catalog view |

### Building from Source

```bash
# Build images
docker-compose build

# Run
docker-compose up
```

### Stopping Services

```bash
docker-compose down
```

---

## Production Considerations

### Security

- The app does NOT store API keys - they're only used in-memory during requests
- No patient data is processed - only clinical algorithm definitions
- Enable HTTPS in production (Vercel/Render handle this automatically)

### Performance

- **Free tier limitations**: Cold starts on Render (~30s first request)
- **Recommendation**: Use Render Starter ($7/mo) for better performance
- **Caching**: Static assets are cached by Vercel's CDN

### Monitoring

- Vercel: Built-in analytics and logs
- Render: Built-in logs and metrics
- Self-hosted: Add your own monitoring (e.g., Prometheus, Grafana)

---

## Troubleshooting

### Backend not responding

```bash
# Check backend logs
docker-compose logs backend

# Verify health endpoint
curl http://localhost:8200/health
```

### Frontend can't reach backend

1. Check `NEXT_PUBLIC_API_URL` is set correctly
2. Ensure backend is running: `docker-compose ps`
3. Check CORS settings in backend

### Ollama not detected

1. Ensure Ollama is running: `ollama serve`
2. Check the host URL in environment variables
3. In Docker, use `host.docker.internal` instead of `localhost`
