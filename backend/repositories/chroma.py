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
            "role": meta["role"],
            "content": doc,
            "timestamp": meta["timestamp"],
        }
        for doc, meta in zip(results["documents"], results["metadatas"])
    ]
    messages.sort(key=lambda m: m["timestamp"])
    return messages


def get_recent_messages(conversation_id: str, limit: int = 20) -> list[dict]:
    """Return the most recent N messages for a conversation."""
    return get_messages(conversation_id)[-limit:]


def delete_conversation(conversation_id: str) -> None:
    """Delete all messages belonging to a conversation."""
    collection = get_collection()
    results = collection.get(
        where={"conversation_id": conversation_id},
        include=[],
    )
    if results["ids"]:
        collection.delete(ids=results["ids"])
