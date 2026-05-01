import os
import uvicorn
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.chat import recommend_router, history_router
from services import llm
from repositories import chroma

load_dotenv(Path(__file__).parent / ".env")

chroma.init_chroma(path=os.getenv("CHROMA_PATH", os.getenv("CHROMA_PATH")))

llm.init_client(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("BASE_URL")
)

app = FastAPI(title="LLM Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend_router, prefix="/api/v1")
app.include_router(history_router,   prefix="/api/v1")




if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1323)
