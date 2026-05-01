# Thailand Tourism Mini Hackathon

AI Travel Matchmaker — matches travelers to Thailand destinations using RAG + Typhoon LLM.

---

## Tech Stack

### Frontend
| Category | Technology |
|----------|-----------|
| Language | Vanilla JavaScript (ES6+), HTML5, CSS3 |
| UI / Icons | Lucide Icons (CDN), CSS Custom Properties, Catppuccin Latte palette |
| Fonts | Google Fonts — Sarabun (Thai), Nunito |
| Markdown | marked.js |
| State | localStorage (UUID-based user ID, conversation history, user profile) |
| HTTP | Fetch API |
| Server | Nginx (Alpine) — gzip, 1-year asset caching, SPA fallback |

### Backend
| Category | Technology |
|----------|-----------|
| Language | Python 3.13+ |
| Framework | FastAPI 0.136 + Uvicorn 0.46 (ASGI) |
| Data validation | Pydantic v2 |
| LLM client | OpenAI Python SDK v2 → Typhoon v2.5-30B (custom base URL) |
| Vector DB | ChromaDB 1.5 (cosine / HNSW, persistent) |
| Embeddings | HuggingFace BAAI/bge-m3 via LangChain-HuggingFace |
| ML stack | PyTorch, Sentence-Transformers, Transformers, scikit-learn, ONNX Runtime |
| Data | Pandas, NumPy, SciPy |
| Async / HTTP | httpx, uvloop, anyio, websockets |
| Observability | OpenTelemetry (OTLP gRPC exporter) + LangSmith |
| Config | python-dotenv, pydantic-settings |
| Serialization | orjson |

### Infrastructure
| Category | Technology |
|----------|-----------|
| Containerisation | Docker + Docker Compose |
| API style | REST + Server-Sent Events (streaming) |
| CORS | Allow-all (development) |

---

## Environment variables

Create a `.env` file at the project root (used by Docker Compose):

```env
TYPHOON_API_KEY=your_typhoon_api_key_here
API_BASE=http://localhost:8000
```

For running the backend locally, also create `backend/.env` with the same content.

---

## Option 1 — Docker Compose

### How it works

| Service | Base image | Port | Notes |
|---------|-----------|------|-------|
| `backend` | `python:3.14-slim` | `8000` | On first start, runs `embeded.py` to build ChromaDB if `chroma_db/` is empty, then starts Uvicorn |
| `frontend` | `nginx:alpine` | `80` | Serves static files with gzip + 1-year asset caching; starts after `backend` |

- `./backend/chroma_db` is bind-mounted into the container so the vector store persists across restarts.
- Backend env vars are loaded from `./backend/.env`.
- Both services restart automatically (`unless-stopped`).

### Commands

```bash
# Build and start both containers
docker compose up --build

# Run in background
docker compose up --build -d

# Stop containers (keeps volumes)
docker compose down

# Stop and remove the chroma_db bind-mount data
docker compose down && rm -rf backend/chroma_db
```

### Service URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| Backend API | http://localhost:8000/api/v1 |
| Swagger docs | http://localhost:8000/api/v1/docs |

### Useful container commands

```bash
# Open a shell in the backend container
docker compose exec backend bash

# Open a shell in the frontend container
docker compose exec frontend sh

# Stream logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild ChromaDB embeddings manually inside the running backend container
docker compose exec backend python embeded.py
```

---

## Option 2 — Run backend locally

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install CPU-only torch first (avoids pulling multi-GB CUDA libraries)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
pip install -r requirements.txt

# Build the ChromaDB vector store (one-time step)
python embed_places.py

# Start the API server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend is available at **http://localhost:8000/api/v1**

---

## Option 3 — Run frontend locally

The frontend is plain HTML — no build step required.

```bash
# Open directly in browser (macOS)
open frontend/index.html

# Or serve with Python to avoid browser CORS restrictions
cd frontend
python -m http.server 3000
# → http://localhost:3000
```

> Make sure `API_BASE` in your `.env` points to the running backend (e.g. `http://localhost:8000`).

---

## API endpoints

All routes are prefixed with `/api/v1`.

| Method   | Path                          | Description                            |
|----------|-------------------------------|----------------------------------------|
| `GET`    | `/`                           | Health check                           |
| `POST`   | `/recommend`                  | Get personalized travel recommendations |
| `POST`   | `/recommend/stream`           | Streaming SSE version of `/recommend`  |
| `POST`   | `/save`                       | Save a place to user's list            |
| `GET`    | `/history`                    | Fetch all conversation histories       |
| `GET`    | `/history/{conversation_id}`  | Fetch history for a conversation       |
| `DELETE` | `/history/{conversation_id}`  | Delete a conversation history          |

Interactive docs (Swagger UI): **http://localhost:8000/docs**

---

## Testing with Postman

Import the collection file:

```
frontend/hack4 Copy.postman_collection.json
```

**How to import:**
1. Open Postman → **Import** → select the `.json` file
2. The collection includes these pre-configured requests:

| Request name    | Method   | URL                                      |
|-----------------|----------|------------------------------------------|
| chat            | POST     | `http://localhost:8000/api/v1/recommend` |
| stream          | POST     | `http://localhost:8000/api/v1/recommend/stream` |
| chat-id         | GET      | `http://localhost:8000/api/v1/history/:id` |
| remove chat-id  | DELETE   | `http://localhost:8000/api/v1/history/:id` |
| chat all        | GET      | `http://localhost:8000/api/v1/history`   |

**Example request body for `POST /recommend`:**

```json
{
  "message": "หิวข้าวแกง",
  "conversation_id": "88",
  "user_profile": {
    "favourite": [],
    "favourite_province": ["ChiangMai", "Kra-bi"],
    "style": ["backpacker", "Nature"],
    "food": ["Noodle", "Seafood"],
    "transportation": ["train"],
    "budget": "mid",
    "avoid_crowd": false,
    "saved_location": []
  }
}
```

---

## Project structure

```
minihack4/
├── docker-compose.yml
├── .env                          # root env — used by Docker Compose
├── backend/
│   ├── Dockerfile
│   ├── .env                      # local env — used for non-Docker runs
│   ├── requirements.txt
│   ├── embed_places.py           # builds ChromaDB vector store (run once)
│   └── src/
│       ├── main.py               # FastAPI app entry point
│       ├── router.py             # API route definitions
│       ├── services.py           # business logic
│       ├── rag.py                # RAG retrieval
│       ├── repository.py         # ChromaDB / data access
│       ├── schemas.py            # Pydantic models
│       └── client.py             # Typhoon/OpenAI client
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── index.html
    ├── hack4 Copy.postman_collection.json
    ├── css/
    ├── js/
    └── assets/
```
