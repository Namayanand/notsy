# Notsy — Claude Context File

## Project Overview

Notsy is an AI-powered knowledge management and learning app for students. Three services:

| Service | Stack | Status |
|---|---|---|
| Frontend | React 18, Vite, Axios, D3, plain CSS | Built — keep React, do NOT rewrite in Astro |
| Backend | Spring Boot 3.2, Java, JWT, WebSocket, Quartz, PostgreSQL | Fully built |
| AI Service | FastAPI, LangGraph, LangChain, ChromaDB, Groq (Llama 3.3 70B) | Built + all bugs fixed |

**Frontend stack decision:** Astro.js is NOT suitable for Notsy. Every component (auth, D3, WebSocket, real-time chat) needs client-side JS — Astro's zero-JS philosophy fights this app. Keep React + Vite.

---

## Repository Structure

```
notsy/
├── frontend/               React app (React 18, Vite, Axios, D3, plain CSS)
│   ├── src/api/            Axios API clients (auth, notebooks, topics, chat, agents, etc.)
│   ├── src/components/     ChatInterface, AgentNetwork, FileUpload, D3 graphs, etc.
│   ├── src/context/        AuthContext (JWT, accessToken/refreshToken in localStorage)
│   ├── src/pages/          Login, Register, Dashboard, Notebook, StudySession, GraphPage, Profile
│   ├── vite.config.js      Proxy /api/* to VITE_API_URL (dev only)
│   └── nginx.conf          Prod: envsubst for $PORT and $API_URL at container start
├── backend/                Spring Boot (Java)
│   └── Dockerfile          PORT-aware: -Dserver.port=$PORT
├── ai-service/             FastAPI AI service
│   ├── main.py             FastAPI entry, CORS from ALLOWED_ORIGINS env var
│   ├── requirements.txt    Python deps (see version changes below)
│   ├── .env                Real secrets — DO NOT COMMIT
│   ├── .env.example        Placeholders only
│   ├── app/
│   │   ├── api/            agent_routes.py, chat.py, embed.py, search.py, study_planner.py
│   │   ├── agents/         langchain_agents.py, langgraph_agents.py, prompts.py
│   │   ├── core/           rag_engine.py, memory_store.py, embeddings.py, orchestrator.py
│   │   │                   graph_builder.py, study_planner.py, document_loader.py
│   │   ├── models/         schemas.py (Pydantic models with validation)
│   │   └── services/       vector_store.py (ChromaDB wrapper)
│   ├── orchestrator/       app.py, graph.py (LangGraph intent classifier)
│   └── evaluation/         run.py (offline RAG eval — ragas not installed in main venv)
├── .github/workflows/      deploy.yml — CI/CD for Railway + Vercel (committed 2026-06-27)
├── .env.example            Root env example (GROQ key is placeholder — real key in ai-service/.env)
└── docker-compose.yml      Local dev reference
```

---

## Local Dev Setup

**Virtual env**: `notsyenv` (Python 3.12) in project root
```bash
# Activate
source notsyenv/Scripts/activate    # Git Bash
notsyenv\Scripts\activate           # PowerShell

# Run AI service
cd ai-service
uvicorn main:app --reload --port 8000

# Docs UI
http://localhost:8000/docs
```

**Env file**: `ai-service/.env` — contains real GROQ_API_KEY. DO NOT COMMIT.

**Routes that work without Spring Boot:**
`POST /agent/langchain/chat`, `POST /agent/langchain/tutor`, `POST /agent/langchain/quiz`, `GET /health`

**Routes that fail without Spring Boot:** anything hitting `/api/memory` or `/api/streaks`

---

## Requirements.txt — Version Changes

| Package | Original | Current | Reason |
|---|---|---|---|
| `chromadb` | `0.4.24` | `0.5.3` | 0.4.x pins chroma-hnswlib==0.7.3 (no Windows wheel) |
| `langchain-core` | `0.3.15` | `0.3.17` | langchain-community 0.3.7 requires >=0.3.17 |
| `ragas` | `0.1.21` | removed | Incompatible with langchain>=0.3; comment-only in requirements.txt |

`constraints.txt` was also deleted — no longer needed since chromadb==0.5.3 resolves chroma-hnswlib automatically.

---

## All Bug Fixes Applied (complete history)

### Session 1 (previous)
| File | Change |
|---|---|
| `rag_engine.py` | regex group fix `group(1)→group(2)` in `parse_grading()` |
| `rag_engine.py` | null-safe history `(history or [])[-10:]` |
| `rag_engine.py` | Groq API wrapped in `_groq_create()` with tenacity retry |
| `rag_engine.py` | model from `GROQ_MODEL` env var (not hardcoded) |
| `embeddings.py` | SentenceTransformer import at module level with try/except |
| `memory_store.py` | ChromaDB metadatas default `[{}]→[[{}]]` |
| `memory_store.py` | `improvement_trend` wired to real assessment scores |
| `agent_routes.py` | Session store → Redis with in-memory fallback |
| `agent_routes.py` | Context persisted via `memory_store.update_session_context()` |
| `agent_routes.py` | LangGraph streaming: `ainvoke()→astream()` + `StreamingResponse` |
| `langchain_agents.py` | JSON parsing: greedy regex → `JSONDecoder.raw_decode()` |
| `langchain_agents.py` | `create_openai_functions_agent` → `create_tool_calling_agent` |
| `langchain_agents.py` | `HumanMessage(content="{input}")` → `("human", "{input}")` |
| `langchain_agents.py` | `AgentExecutor` import moved to `langchain.agents` |
| `langgraph_agents.py` | JSON parsing: same `raw_decode()` fix |
| `langgraph_agents.py` | `tutor_node` reads `learning_mode` from `LearningState` |
| `vector_store.py` | `chromadb.Client()` → `chromadb.PersistentClient()` |
| `vector_store.py` | `list_collections()`: `.get("name")` → `.name` attribute |
| `main.py` | CORS from `ALLOWED_ORIGINS` env var (no wildcard `*`) |

### Session 2 (2026-06-27)
| File | Change |
|---|---|
| `app/core/graph_builder.py` | hardcoded `"llama3-70b-8192"` → `os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")` |
| `app/core/study_planner.py` | same model fix in `StudyPlannerAgent` constructor |
| `app/api/study_planner.py` | same model fix in `generate_flashcards` + `generate_quiz` + added `import os` |
| `app/api/agent_routes.py` | `/registry` descriptions: `→` → `->` (UTF-8 fix) |
| `app/api/search.py` | double prefix removed: `/search/semantic` → `/semantic`, `/search/global` → `/global` |
| `app/api/embed.py` | double prefix removed: `/embed` → `""`, `/embed/topic/{id}` → `/topic/{id}`, etc. |
| `app/api/agent_routes.py` | `StartSessionRequest.goal` — `Field(..., min_length=1)` + added `Field` import |
| `app/models/schemas.py` | `ChatRequest.message` — `Field(..., min_length=1)` |
| `app/models/schemas.py` | `ChatRequest.learning_mode` — `pattern=` constraint for valid modes |
| `app/api/search.py` | `SemanticSearchRequest.query` — `Field(..., min_length=1)` |
| `app/models/schemas.py` | `EmbedResourceRequest` — `gt=0` on resource_id, `pattern=` on file_type, `@model_validator` for file_path/source_url |
| `app/services/vector_store.py` | `delete_collection()` returns `"deleted"`/`"not_found"`/`"error"` instead of bool |
| `app/api/embed.py` | DELETE endpoint maps to 200/404/500 based on new return value |
| `app/agents/langgraph_agents.py` | `ainvoke_stream`: `graph.ainvoke()` → `graph.astream()` |
| `app/agents/langgraph_agents.py` | Removed conflicting `add_edge("memory","retriever")` — only conditional edge remains |
| `app/core/orchestrator.py` | Registered all 6 named agents: `langchain`, `learning`, `tutor`, `evaluator`, `planner`, `summariser`, `langgraph` |
| `app/core/rag_engine.py` | `_self_rag_generate()` — added `history` param, injects last 10 messages before user turn |

**Clean API paths after double-prefix fix:**
`POST /search/semantic`, `POST /search/global`, `POST /embed`, `DELETE /embed/topic/{id}`, `GET /embed/status/{id}`

### Session 3 (2026-06-27) — Phase A + Phase C pre-go-live fixes

**Phase A — Version control / deployment config**
| File | Change |
|---|---|
| `docker-compose.yml` | `VITE_API_BASE_URL` → `API_URL` (nginx reads `$API_URL`, not Vite build var) |
| `docker-compose.yml` | GROQ_MODEL default `llama-3-70b-8192` → `llama-3.3-70b-versatile` |
| `frontend/Dockerfile` | Added `ARG VITE_API_URL` baked at build time; `envsubst '$PORT $API_URL'` at runtime |
| `frontend/nginx.conf` | `listen 3000` → `listen ${PORT}`; `proxy_pass http://backend:8080` → `proxy_pass ${API_URL}` |
| `frontend/vite.config.js` | `loadEnv` so `VITE_API_URL` resolves correctly in proxy target |
| `frontend/src/api/agents.js` | Derive WebSocket URL from `VITE_API_URL` when `VITE_WS_URL` absent |
| `frontend/src/components/ChatInterface.jsx` | Remove hardcoded `localhost:8080` fallback in stream URLs |
| `frontend/src/components/AgentNetwork/AgentGraph.jsx` | Orchestrator URL reads `VITE_AI_URL` / `VITE_API_URL` env vars |
| `.env.example` | Scrubbed real GROQ API key → placeholder |
| `ai-service/.env.example` | Scrubbed real GROQ key; added `GROQ_MODEL`, `BACKEND_URL`, `ALLOWED_ORIGINS`, `AI_SERVICE_URL` |
| `.gitignore` | Removed `CLAUDE.md` exclusion so project instructions are tracked |
| `.github/workflows/deploy.yml` | **Committed** — CI/CD pipeline for Railway (backend + AI) + Vercel (frontend) |
| `ai-service/railway.json` | **Committed** — Railway service config (Dockerfile builder, restart policy) |
| `backend/railway.json` | **Committed** — Railway service config (PORT-aware Spring Boot start command) |
| `frontend/railway.json` | **Committed** — Railway service config (VITE_API_URL build arg) |

### Session 4 (2026-06-27) — Backend compile fixes (Railway deploy)
| File | Change |
|---|---|
| `backend/.../service/QuizService.java` | Added missing `import com.notsy.dto.response.QuizQuestionResponse` — it's a top-level class, not nested in `QuizResponse`, so the wildcard `QuizResponse.*` didn't cover it |
| `backend/.../a2a/A2ATaskHistoryController.java` | `user.getId()` returns `Long` but `A2ATask.userId` is `UUID`; replaced `UUID.fromString(...)` ternary with `new UUID(0, user.getId())` for deterministic mapping (both call sites) |
| `backend/.../a2a/A2AController.java` | Added explicit `<Map<String,Object>>` type witness on `notFound().build()` so javac resolves the `Mono<ResponseEntity<Map<String,Object>>>` return type |

**Phase C — Pre-go-live architectural fixes (all three now done)**
| File | Change |
|---|---|
| `app/core/memory_store.py` | `_store_in_backend()`: sync `requests.post()` → async `httpx.AsyncClient` — no longer blocks event loop |
| `orchestrator/graph.py` | Added `OrchestratorGraph.get_compiled()` — compiles graph once, caches in `self._compiled`; `run_orchestrator()` and `get_orchestrator_graph()` now use cached version |
| `orchestrator/graph.py` | Hardcoded `"llama-3-70b-8192"` default → `"llama-3.3-70b-versatile"` in `__init__` |
| `app/api/agent_routes.py` | `/registry` endpoint: hardcoded `http://localhost:8000` → `os.getenv("AI_SERVICE_URL", "http://localhost:8000")` |
| `ai-service/.env.example` | Added `AI_SERVICE_URL=http://localhost:8000` |

---

## Deployment Plan

### Phase A — Version Control (Do First)
1. Fix `docker-compose.yml`: frontend service uses `VITE_API_BASE_URL` but Dockerfile/nginx expect `API_URL` — rename to `API_URL: http://backend:8080`
2. Commit all unstaged bug fixes
3. Commit untracked files: `.github/`, `railway.json` × 3, `CLAUDE.md`
4. Create GitHub remote + push

### Phase B — Railway + Vercel Setup (manual, in this order)
**Accounts needed:** railway.app (free) + vercel.com (free, link to GitHub)

**Railway service creation order** (dependencies matter):
1. PostgreSQL plugin → auto-sets `DATABASE_URL`
2. Redis plugin → auto-sets `REDIS_URL`
3. AI service → root dir `ai-service`, env vars:
   - `GROQ_API_KEY`, `GROQ_MODEL=llama-3.3-70b-versatile`
   - `ALLOWED_ORIGINS` = Vercel URL (add after step 5)
   - `CHROMA_PERSIST_DIR=./chroma_db`, `UPLOAD_BASE_DIR=./uploads`, `ENABLE_SELF_RAG=true`
4. Backend → root dir `backend`, env vars:
   - `SPRING_DATASOURCE_URL/USERNAME/PASSWORD` from PostgreSQL plugin
   - `SPRING_REDIS_HOST` from Redis plugin
   - `JWT_SECRET` (generate strong random string)
   - `AI_ORCHESTRATOR_URL` = Railway AI service public URL
5. Get Railway token → add as `RAILWAY_TOKEN` in GitHub repo secrets

**Vercel:**
1. Import GitHub repo → root dir `frontend/`
2. Set `VITE_API_URL` = Railway backend public URL
3. Copy Vercel URL → add to Railway AI service `ALLOWED_ORIGINS`
4. Add to GitHub secrets: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`

After this, every push to `master` auto-deploys via `.github/workflows/deploy.yml`.

### Phase C — Architectural Issues

| Priority | Issue | File | Status |
|---|---|---|---|
| 1 | Sync `requests.post()` in async `_store_in_backend()` | `app/core/memory_store.py` | **FIXED (Session 3)** — replaced with `httpx.AsyncClient` |
| 2 | LangGraph graph recompiled on every request | `orchestrator/graph.py` | **FIXED (Session 3)** — `get_compiled()` caches compiled graph |
| 3 | Hardcoded `http://localhost:8000` in `get_agent_registry()` | `app/api/agent_routes.py` | **FIXED (Session 3)** — reads `AI_SERVICE_URL` env var |
| 4 — can wait | SentenceTransformer vectors computed then discarded | `app/core/embeddings.py` | Wasted compute only |
| 5 — can wait | TTL silently ignored in `InMemoryStore` | `app/core/memory_store.py` | Memory leak risk |
| 6 — can wait | Duplicate PDF parsing in `evaluation/run.py` | `evaluation/run.py` | Offline eval only |

---

## Known Config Issues

- `ai-service/.env` is implicitly protected by root `.env` glob in `.gitignore` — safe, but adding an explicit entry would be clearer

---

## Next Steps

### Phase A — DONE (2026-06-27)
- [x] Fix `docker-compose.yml` `VITE_API_BASE_URL` → `API_URL`
- [x] Commit all unstaged changes + untracked deployment files
- [x] Push to GitHub remote

### Phase C issues 1-3 — DONE (2026-06-27)
- [x] Replace sync `requests.post()` with async `httpx` in `memory_store.py._store_in_backend()`
- [x] Compile LangGraph graph once at startup in `orchestrator/graph.py`
- [x] Replace hardcoded `localhost:8000` in `agent_routes.py get_agent_registry()`

### Deployment (Phase B — manual setup by user, IN PROGRESS)
- [ ] Create Railway project + add PostgreSQL + Redis plugins
- [ ] Deploy AI service to Railway (root dir: `ai-service`) — set env vars incl. `AI_SERVICE_URL`
- [ ] Deploy backend to Railway (root dir: `backend`) — set `AI_ORCHESTRATOR_URL` to AI service URL
- [ ] Deploy frontend to Vercel (root dir: `frontend`) — set `VITE_API_URL` to backend URL
- [ ] Update Railway AI service `ALLOWED_ORIGINS` with Vercel URL + redeploy
- [ ] Add GitHub Actions secrets: `RAILWAY_TOKEN`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`
- [ ] End-to-end smoke test: register → login → notebook → upload PDF → chat

### Future
- [ ] Architectural issues 4-6 (lower priority)
- [ ] Backend Spring Boot deep-dive sessions (collaborative learning)
