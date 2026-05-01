from src.rag import get_recommendations, generate_ai_reasons, generate_ai_reasons_stream, generate_suggested_prompts
from src.repository import (
    save_message,
    get_conversation_history,
    delete_conversation_history,
    get_all_conversations,
    save_conversation_nickname,
    get_conversation_nickname,
)


def _resolve_nickname(conversation_id: str | None, nickname: str | None) -> str | None:
    """
    Persist a new nickname when provided, then return the active nickname for
    this conversation (falls back to the stored value if not sent this turn).
    """
    if not conversation_id:
        return nickname
    if nickname:
        save_conversation_nickname(conversation_id, nickname)
        return nickname
    return get_conversation_nickname(conversation_id)


def get_travel_recommendations(
    profile_dict: dict,
    message: str = "",
    top_k: int = 3,
    conversation_id: str = None,
    nickname: str | None = None,
):
    """
    Orchestrates the full recommendation flow:
    1. Resolve / persist nickname for this conversation
    2. Retrieve top matching places from ChromaDB
    3. Generate AI explanation via Groq (with nickname in system prompt)
    4. Generate follow-up prompt suggestions
    5. Persist user message + AI reply to chat history (if conversation_id given)

    Returns (top_places, ai_reason, suggested_prompts)
    """
    active_nickname = _resolve_nickname(conversation_id, nickname)

    top_places = get_recommendations(
        user_profile=profile_dict,
        message=message,
        top_k=top_k,
    )

    ai_reason = generate_ai_reasons(
        places=top_places,
        user_profile=profile_dict,
        message=message,
        nickname=active_nickname,
    )

    suggested_prompts = generate_suggested_prompts(top_places, profile_dict)

    if conversation_id:
        save_message(conversation_id, "user", message)
        save_message(conversation_id, "assistant", ai_reason)

    return top_places, ai_reason, suggested_prompts


def get_travel_recommendations_stream(
    profile_dict: dict,
    message: str = "",
    top_k: int = 3,
    conversation_id: str = None,
    nickname: str | None = None,
):
    """
    Streaming variant — returns places + suggested_prompts immediately,
    plus a generator that yields AI response chunks token-by-token.

    The caller is responsible for accumulating chunks and saving the
    assistant message to history after streaming completes.

    Returns (top_places, suggested_prompts, ai_chunk_generator)
    """
    active_nickname = _resolve_nickname(conversation_id, nickname)

    top_places = get_recommendations(
        user_profile=profile_dict,
        message=message,
        top_k=top_k,
    )

    suggested_prompts = generate_suggested_prompts(top_places, profile_dict)

    if conversation_id:
        save_message(conversation_id, "user", message)

    ai_stream = generate_ai_reasons_stream(
        places=top_places,
        user_profile=profile_dict,
        message=message,
        nickname=active_nickname,
    )

    return top_places, suggested_prompts, ai_stream


# =============================================================================
# Chat History Services
# =============================================================================

def add_message(conversation_id: str, role: str, content: str) -> str:
    """Save a single message to the conversation history."""
    return save_message(conversation_id, role, content)


def fetch_conversation_history(conversation_id: str) -> dict:
    """Get all messages for a given conversation."""
    messages = get_conversation_history(conversation_id)
    return {
        "conversation_id": conversation_id,
        "message_count": len(messages),
        "messages": messages,
    }


def remove_conversation_history(conversation_id: str) -> dict:
    """Delete all messages for a given conversation."""
    deleted_count = delete_conversation_history(conversation_id)
    return {
        "conversation_id": conversation_id,
        "deleted_count": deleted_count,
        "success": True,
    }


def fetch_all_conversations() -> dict:
    """Get every conversation with their messages."""
    conversations = get_all_conversations()
    return {
        "total_conversations": len(conversations),
        "conversations": conversations,
    }


def save_place_to_list(place_name: str, current_saved: list) -> tuple[list, bool]:
    """
    Adds place_name to the saved list if not already present.

    Returns (updated_list, already_saved)
    """
    updated = list(current_saved)
    if place_name in updated:
        return updated, True
    updated.append(place_name)
    return updated, False
