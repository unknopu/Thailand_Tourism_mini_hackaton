import openai
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import llm
from repositories import chroma

recommend_router = APIRouter(prefix="/recommend", tags=["recommend"])
history_router   = APIRouter(prefix="/history",   tags=["history"])


class UserProfile(BaseModel):
    favourite:          list[str] = []
    favourite_province: list[str] = []
    style:              list[str] = []
    food:               list[str] = []
    transportation:     list[str] = []
    budget:             str       = "mid"
    avoid_crowd:        bool      = False
    saved_location:     list[str] = []


class ChatRequest(BaseModel):
    message:         str
    conversation_id: str         = "default"
    nick_name:       str         = ""
    user_profile:    UserProfile = UserProfile()


class ChatResponse(BaseModel):
    response: str


# ─── /api/v1/recommend ────────────────────────────────────────────────────────

@recommend_router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message and receive the full response as JSON."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        response_text = await llm.ask(
            request.message,
            request.conversation_id,
            request.user_profile.model_dump(),
        )
    except openai.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid API key")
    except openai.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit reached, please retry later")
    except openai.APIError as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e.message}")

    return ChatResponse(response=response_text)


@recommend_router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Send a message and receive the response as a Server-Sent Events stream."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    async def token_generator():
        try:
            async for text in llm.ask_stream(
                request.message,
                request.conversation_id,
                request.user_profile.model_dump(),
            ):
                yield f"data: {text}\n\n"
            yield "data: [DONE]\n\n"
        except openai.APIError as e:
            yield f"data: [ERROR] {e.message}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


# ─── /api/v1/history ──────────────────────────────────────────────────────────

@history_router.get("")
async def get_all_history():
    """Return all conversations."""
    conversations = chroma.get_all_conversations()
    return {"total_conversations": len(conversations), "conversations": conversations}


@history_router.get("/{conversation_id}")
async def get_history(conversation_id: str):
    """Return all stored messages for a conversation."""
    messages = chroma.get_messages(conversation_id)
    return {
        "conversation_id": conversation_id,
        "message_count":   len(messages),
        "messages":        messages,
    }


@history_router.delete("/{conversation_id}")
async def clear_history(conversation_id: str):
    """Delete all messages for a conversation."""
    deleted_count = chroma.delete_conversation(conversation_id)
    return {
        "conversation_id": conversation_id,
        "deleted_count":   deleted_count,
        "success":         True,
    }


# ─── Health ───────────────────────────────────────────────────────────────────

@recommend_router.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
