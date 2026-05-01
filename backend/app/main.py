from dotenv import load_dotenv
from fastapi import FastAPI

from backend.app.routers import chat

load_dotenv()

app = FastAPI(title="LLM Chat API")

app.include_router(chat.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
