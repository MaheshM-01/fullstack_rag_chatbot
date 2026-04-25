# RAG Chatbot Portfolio Project

End-to-end Retrieval Augmented Generation (RAG) chatbot with:
- `apps/worker`: FastAPI + ChromaDB + Groq LLM integration
- `apps/api`: NestJS API (auth, chat sessions, document ingestion orchestration)
- `apps/web`: Next.js frontend (auth, chat, uploads, session management)
- `infrastructure/docker`: Docker Compose for full local stack

## Phase Status

- `Phase 1 (Python Worker)`: Done
- `Phase 2 (NestJS API)`: Done with hardening
- `Phase 3 (Next.js Frontend)`: Done
- `Phase 4 (Docker + README)`: Done
- `Phase 5 (Git Push)`: Ready checklist included below

## Tech Stack

- LLM: Groq API (free tier friendly)
- Embeddings: `sentence-transformers` (`all-MiniLM-L6-v2`)
- Vector DB: ChromaDB (persistent local storage)
- Worker: FastAPI
- Backend: NestJS + TypeORM + PostgreSQL
- Frontend: Next.js App Router + TypeScript
- Infra: Docker Compose

## Monorepo Layout

```text
apps/
  api/       # NestJS backend
  web/       # Next.js frontend
  worker/    # FastAPI RAG worker
docs/
  architecture.md
  api-reference.md
infrastructure/docker/
  docker-compose.yml
scripts/
  seed.py
  eval.py
```

## Prerequisites

- Node.js 20+
- Python 3.11+
- PostgreSQL (local or Docker)
- Groq API key (free tier)

## Environment Setup

```bash
cp .env.example .env
```

Minimum required values in `.env`:
- `GROQ_API_KEY`
- `JWT_SECRET`
- DB values (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)

## Run Locally (Without Docker)

### 1) Install Node dependencies

```bash
npm install
```

### 2) Start backend API

```bash
npm run dev:api
```

### 3) Start frontend

```bash
npm run dev:web
```

### 4) Start Python worker

```bash
cd apps/worker
pip install -r requirements.txt
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend: `http://localhost:3000`  
NestJS API: `http://localhost:3001/api`  
Worker API docs: `http://localhost:8000/docs`

## Run With Docker

```bash
docker compose -f infrastructure/docker/docker-compose.yml up --build
```

Services:
- Web: `http://localhost:3000`
- API: `http://localhost:3001/api`
- Worker: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

## Useful Scripts

Seed worker from file/URL:

```bash
python scripts/seed.py --source apps/worker/test_doc.txt --namespace default
python scripts/seed.py --source https://example.com --namespace docs
```

Run basic QA evaluation:

```bash
python scripts/eval.py --dataset scripts/sample_eval.json --namespace default
```

## API Docs

- Architecture: `docs/architecture.md`
- Endpoint reference: `docs/api-reference.md`

## Free Tier Groq Tips

- Keep `RAG_TOP_K` moderate (`4-6`) to control prompt size
- Keep answers concise to reduce tokens
- Reuse chat sessions; avoid unnecessary retries
- Use document scoping (`namespace`) for focused retrieval

## Phase 5: Git Push Checklist

1. Initialize git if needed:
   ```bash
   git init
   ```
2. Create a clean branch:
   ```bash
   git checkout -b feature/end-to-end-rag
   ```
3. Stage and commit:
   ```bash
   git add .
   git commit -m "Complete end-to-end RAG portfolio stack (worker, API, web, docker, docs)"
   ```
4. Add remote and push:
   ```bash
   git remote add origin <your-repo-url>
   git push -u origin feature/end-to-end-rag
   ```
5. Open PR with screenshots (auth, upload, chat, session history) and architecture summary.
