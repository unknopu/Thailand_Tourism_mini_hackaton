import openai
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import llm
from repositories import chroma

router = APIRouter(prefix="/chat", tags=["chat"])


class UserProfile(BaseModel):
    favourite_province: list[str] = []
    style: list[str] = []
    food: list[str] = []
    transportation: list[str] = []


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"
    user_profile: UserProfile = UserProfile()


class ChatResponse(BaseModel):
    response: str


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message and receive the full response as JSON."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        response_text = await llm.ask(request.message, request.conversation_id, request.user_profile.model_dump())
    except openai.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key")
    except openai.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit reached, please retry later")
    except openai.APIError as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e.message}")

    return ChatResponse(response=response_text)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Send a message and receive the response as a Server-Sent Events stream."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    async def token_generator():
        try:
            async for text in llm.ask_stream(request.message, request.conversation_id, request.user_profile.model_dump()):
                yield f"data: {text}\n\n"
            yield "data: [DONE]\n\n"
        except openai.APIError as e:
            yield f"data: [ERROR] {e.message}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")

@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str):
    """Return all stored messages for a conversation."""
    messages = chroma.get_messages(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages}


@router.delete("/history/{conversation_id}")
async def clear_history(conversation_id: str):
    """Delete all messages for a conversation."""
    chroma.delete_conversation(conversation_id)
    return {"conversation_id": conversation_id, "status": "cleared"}


@router.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}