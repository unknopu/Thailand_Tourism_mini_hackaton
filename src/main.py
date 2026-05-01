from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.router import router
import uvicorn
import signal
import asyncio

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