import uuid
import time

import chromadb
from chromadb.config import Settings

CHROMA_DB_PATH = "chroma_db"
HISTORY_COLLECTION_NAME = "chat_history"
PROFILES_COLLECTION_NAME = "conversation_profiles"

_client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH,
    settings=Settings(anonymized_telemetry=False),
)
history_collection = _client.get_or_create_collection(name=HISTORY_COLLECTION_NAME)
profiles_collection = _client.get_or_create_collection(name=PROFILES_COLLECTION_NAME)


# =============================================================================
# Chat History Repository
# =============================================================================

def save_message(conversation_id: str, role: str, content: str) -> str:
    """Persist a single message to the chat_history collection."""
    message_id = f"{conversation_id}_{uuid.uuid4().hex}"
    history_collection.add(
        ids=[message_id],
        documents=[content],
        metadatas=[{
            "conversation_id": conversation_id,
            "role": role,
            "timestamp": time.time(),
        }],
    )
    return message_id


def get_conversation_history(conversation_id: str) -> list:
    """Return all messages for a conversation, sorted by timestamp."""
    results = history_collection.get(
        where={"conversation_id": conversation_id},
        include=["documents", "metadatas"],
    )

    messages = [
        {
            "id": results["ids"][i],
            "role": results["metadatas"][i]["role"],
            "content": results["documents"][i],
            "timestamp": results["metadatas"][i]["timestamp"],
        }
        for i in range(len(results["ids"]))
    ]

    messages.sort(key=lambda x: x["timestamp"])
    return messages


def delete_conversation_history(conversation_id: str) -> int:
    """Delete all messages for a conversation. Returns number of deleted messages."""
    results = history_collection.get(
        where={"conversation_id": conversation_id},
        include=[],
    )
    ids = results["ids"]
    if ids:
        history_collection.delete(ids=ids)
    return len(ids)


# =============================================================================
# Conversation Profile Repository (nickname, etc.)
# =============================================================================

def save_conversation_nickname(conversation_id: str, nickname: str) -> None:
    """Upsert the nickname for a conversation (one record per conversation_id)."""
    profiles_collection.upsert(
        ids=[conversation_id],
        documents=[nickname],
        metadatas=[{"conversation_id": conversation_id, "nickname": nickname}],
    )


def get_conversation_nickname(conversation_id: str) -> str | None:
    """Return the stored nickname for a conversation, or None if not set."""
    try:
        result = profiles_collection.get(
            ids=[conversation_id],
            include=["documents"],
        )
        if result["ids"]:
            return result["documents"][0]
        return None
    except Exception:
        return None


def get_all_conversations() -> list:
    """Return every conversation grouped by conversation_id."""
    results = history_collection.get(include=["documents", "metadatas"])

    conversations: dict = {}
    for i in range(len(results["ids"])):
        conv_id = results["metadatas"][i]["conversation_id"]
        if conv_id not in conversations:
            conversations[conv_id] = {
                "conversation_id": conv_id,
                "message_count": 0,
                "messages": [],
            }
        conversations[conv_id]["message_count"] += 1
        conversations[conv_id]["messages"].append({
            "id": results["ids"][i],
            "role": results["metadatas"][i]["role"],
            "content": results["documents"][i],
            "timestamp": results["metadatas"][i]["timestamp"],
        })

    for conv in conversations.values():
        conv["messages"].sort(key=lambda x: x["timestamp"])

    return list(conversations.values())
