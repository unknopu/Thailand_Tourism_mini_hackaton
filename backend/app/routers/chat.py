import anthropic
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.services import llm

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message and receive the full response as JSON."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        response_text = await llm.ask(request.message)
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit reached, please retry later")
    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e.message}")

    return ChatResponse(response=response_text)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Send a message and receive the response as a Server-Sent Events stream."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    async def token_generator():
        try:
            async for text in llm.ask_stream(request.message):
                yield f"data: {text}\n\n"
            yield "data: [DONE]\n\n"
        except anthropic.APIError as e:
            yield f"data: [ERROR] {e.message}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")
