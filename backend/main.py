import os
import signal
import asyncio
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from routers import chat
from services import llm

load_dotenv(".env")

llm.init_client(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("BASE_URL")
)

app = FastAPI(title="LLM Chat API")

app.include_router(chat.router, prefix="/api/v1")




if __name__ == "__main__":
    server = uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=1323)
    )

    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(server.shutdown()))

    loop.run_until_complete(server.serve())
