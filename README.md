# 🌴 AI Travel Matchmaker — Backend

> RAG-powered travel recommendation API for international tourists exploring Thailand.  
> Built for **SuperAI Level 2 Mini Hackathon**

---

## 📐 Architecture Overview

```
Frontend (Chat UI)
      │
      │  POST /recommend  { message, conversation_id, user_profile }
      ▼
FastAPI (main.py)
      │
      ▼
RAG Engine (rag.py)
  ├── ChromaDB  ←  Vector search (BAAI/bge-m3 embeddings)
  └── Groq API  ←  LLaMA 3.3 generates English response
```

---

## 🚀 Quickstart

### 1. Clone & switch to backend branch
```bash
git clone https://github.com/unknopu/Thailand_Tourism_mini_hackaton.git
cd Thailand_Tourism_mini_hackaton
git checkout backend-rag
```

### 2. Create virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file in the project root (never commit this file):
```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```
Get your free API key at → [console.groq.com](https://console.groq.com)

### 5. Build the vector database (first time only)
```bash
python embed_places.py
```
This reads `data/places.csv` and stores embeddings in `chroma_db/`.

### 6. Start the server
```bash
uvicorn src.main:app --reload --port 8000
```
API is now running at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

---

## 📡 API Endpoints

### `POST /recommend`
Get personalized place recommendations based on user profile and chat message.

**Request body:**
```json
{
  "message": "I want somewhere quiet, not too crowded",
  "conversation_id": "88",
  "user_profile": {
    "favourite": [],
    "favourite_province": ["Chumphon", "Krabi"],
    "style": ["nature", "backpacker"],
    "food": ["seafood", "street food"],
    "transportation": ["boat", "train"],
    "budget": "low",
    "avoid_crowd": true,
    "saved_location": []
  }
}
```

**Response:**
```json
{
  "conversation_id": "88",
  "message": "I want somewhere quiet, not too crowded",
  "recommendations": [
    {
      "id": "place_001",
      "name": "Mu Ko Chumphon National Park",
      "province": "Chumphon",
      "match_score": 0.82,
      "crowd_level": 3,
      "hidden_gem_score": 0.5
    }
  ],
  "ai_reason": "Since you love quiet nature spots on a low budget, Mu Ko Chumphon is a perfect fit...",
  "suggested_prompts": [
    "How do I get to Mu Ko Chumphon National Park?",
    "What are the best local foods near Chumphon?",
    "Show me more hidden gems in Chumphon.",
    "Save this place to my list"
  ]
}
```

---

### `POST /save`
Save a place to the user's list. Backend returns the updated list — frontend stores it in localStorage and sends it back with every future request as `saved_location`.

**Request body:**
```json
{
  "conversation_id": "88",
  "place_id": "place_001",
  "place_name": "Mu Ko Chumphon National Park",
  "current_saved": []
}
```

**Response:**
```json
{
  "success": true,
  "message": "'Mu Ko Chumphon National Park' has been saved to your list! 📍",
  "updated_saved_location": ["Mu Ko Chumphon National Park"]
}
```

---

## 💾 Save Feature Flow

```
User clicks Save
      │
      ▼
POST /save  →  returns updated_saved_location
      │
      ▼
Frontend stores list in localStorage
      │
      ▼
Next POST /recommend includes saved_location in user_profile
      │
      ▼
RAG boosts similar places (+0.05 score) & AI skips already-saved places
```

---

## 🧠 Match Score Formula

```
Match Score = (Similarity × 0.5)
            + (Hidden Gem Score × 0.3)
            + ((1 − Crowd Level / 10) × 0.2)
            + (Saved Location Bonus: +0.05 if similar to saved places)
```

- **Similarity** — vector cosine similarity from ChromaDB  
- **Hidden Gem Score** — how undiscovered the place is (0.0 – 1.0)  
- **Crowd Level** — 1 (empty) → 10 (very crowded), lower = better score  

---

## 📁 Project Structure

```
AITravelChatWebsite/
├── src/
│   ├── main.py          # FastAPI app & endpoints
│   └── rag.py           # RAG logic (search + scoring + AI generation)
├── data/
│   └── places.csv       # Place database
├── chroma_db/           # Auto-generated vector database (do not commit)
├── embed_places.py      # Script to build vector DB from CSV
├── requirements.txt
├── .env                 # API keys (do not commit)
└── .env.example         # Template for teammates
```

---

## ⚙️ Requirements

- Python 3.10+
- Groq API key (free tier is fine)
- ~2 GB disk space for the embedding model (BAAI/bge-m3, downloads automatically)

---

## 🔒 Security Notes

- **Never commit `.env`** — it contains your API key
- `chroma_db/` is excluded from git (large binary files)
- `__pycache__/` and `.venv/` are excluded from git

---

## 👥 Team

SuperAI Level 2 — Hackathon Group 4
