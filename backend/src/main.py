import os
import uvicorn
import signal
import asyncio
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.router import router
from src import client as client_module

load_dotenv(override=False)

# Initialize OpenAI client here and inject into the client module so that
# rag.py (which sits downstream in the import chain) can reference it without
# causing a circular import.
client_module.groq_client = OpenAI(
    api_key=os.environ.get("TYPHOON_API_KEY"),
    base_url="https://api.opentyphoon.ai/v1"
)

app = FastAPI(title="AI Travel Matchmaker API", version="2.0")
app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.include_router(router)

if __name__ == "__main__":
    server = uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=8000)
    )

    # gracefully shutting down
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(server.shutdown()))
    loop.run_until_complete(server.serve())
