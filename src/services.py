from src.rag import get_recommendations, generate_ai_reasons, generate_suggested_prompts
from src.repository import (
    save_message,
    get_conversation_history,
    delete_conversation_history,
    get_all_conversations,
)


def get_travel_recommendations(
    profile_dict: dict,
    message: str = "",
    top_k: int = 3,
    conversation_id: str = None,
):
    """
    Orchestrates the full recommendation flow:
    1. Retrieve top matching places from ChromaDB
    2. Generate AI explanation via Groq
    3. Generate follow-up prompt suggestions
    4. Persist user message + AI reply to chat history (if conversation_id given)

    Returns (top_places, ai_reason, suggested_prompts)
    """
    top_places = get_recommendations(
        user_profile=profile_dict,
        message=message,
        top_k=top_k,
    )

    ai_reason = generate_ai_reasons(
        places=top_places,
        user_profile=profile_dict,
        message=message,
    )

    suggested_prompts = generate_suggested_prompts(top_places, profile_dict)

    if conversation_id:
        save_message(conversation_id, "user", message)
        save_message(conversation_id, "assistant", ai_reason)

    return top_places, ai_reason, suggested_prompts


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
