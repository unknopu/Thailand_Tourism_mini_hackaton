import time
import chromadb
from chromadb import Collection

_client: chromadb.ClientAPI | None = None
_collection: Collection | None = None

COLLECTION_NAME = "chat_history"


def init_chroma(path: str = "./chroma_data") -> None:
    """Initialize ChromaDB persistent client and ensure collection exists."""
    global _client, _collection
    _client = chromadb.PersistentClient(path=path)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"[*] chromadb connected — collection: {COLLECTION_NAME!r}")


def get_collection() -> Collection:
    if _collection is None:
        raise RuntimeError("ChromaDB not initialized. Call init_chroma() first.")
    return _collection


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def add_message(conversation_id: str, role: str, content: str) -> None:
    """Store a single message in the collection."""
    collection = get_collection()
    doc_id = f"{conversation_id}_{int(time.time() * 1000)}"
    collection.add(
        ids=[doc_id],
        documents=[content],
        metadatas=[{
            "conversation_id": conversation_id,
            "role": role,
            "timestamp": time.time(),
        }],
    )


def get_messages(conversation_id: str) -> list[dict]:
    """Return all messages for a conversation, ordered by timestamp."""
    collection = get_collection()
    results = collection.get(
        where={"conversation_id": conversation_id},
        include=["documents", "metadatas"],
    )
    if not results["ids"]:
        return []

    messages = [
        {
            "id":        doc_id,
            "role":      meta["role"],
            "content":   doc,
            "timestamp": meta["timestamp"],
        }
        for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
    ]
    messages.sort(key=lambda m: m["timestamp"])
    return messages


def get_recent_messages(conversation_id: str, limit: int = 20) -> list[dict]:
    """Return the most recent N messages for a conversation."""
    return get_messages(conversation_id)[-limit:]


def delete_conversation(conversation_id: str) -> int:
    """Delete all messages belonging to a conversation. Returns number of deleted messages."""
    collection = get_collection()
    results = collection.get(
        where={"conversation_id": conversation_id},
        include=[],
    )
    count = len(results["ids"])
    if results["ids"]:
        collection.delete(ids=results["ids"])
    return count


def get_all_conversations() -> list[dict]:
    """Return all conversations grouped by conversation_id, each sorted by timestamp."""
    collection = get_collection()
    results = collection.get(include=["documents", "metadatas"])

    if not results["ids"]:
        return []

    grouped: dict[str, list[dict]] = {}
    for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
        conv_id = meta["conversation_id"]
        grouped.setdefault(conv_id, []).append({
            "id":        doc_id,
            "role":      meta["role"],
            "content":   doc,
            "timestamp": meta["timestamp"],
        })

    conversations = []
    for conv_id, messages in grouped.items():
        messages.sort(key=lambda m: m["timestamp"])
        conversations.append({
            "conversation_id": conv_id,
            "message_count":   len(messages),
            "messages":        messages,
        })

    return conversations
