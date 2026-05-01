from typing import AsyncGenerator
from openai import OpenAI

from repositories import chroma

_client: OpenAI | None = None
_model: str = "typhoon-v2.5-30b-a3b-instruct"

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Answer questions clearly and concisely."
)


def init_client(api_key: str, base_url: str) -> None:
    global _client
    print(f"[*] llm configurated")
    _client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )


def _build_messages(conversation_id: str, new_message: str) -> list[dict]:
    """Build the full message list: system prompt + history + new user message."""
    history = chroma.get_recent_messages(conversation_id, limit=20)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for entry in history:
        messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": new_message})
    return messages


async def ask(message: str, conversation_id: str = "default") -> str:
    """Send a message and return the complete text response, with persisted history."""
    chroma.add_message(conversation_id, "user", message)

    response = _client.chat.completions.create(
        model=_model,
        max_tokens=8000,
        messages=_build_messages(conversation_id, message),
    )

    assistant_message = response.choices[0].message.content or ""
    chroma.add_message(conversation_id, "assistant", assistant_message)
    return assistant_message


async def ask_stream(message: str, conversation_id: str = "default") -> AsyncGenerator[str, None]:
    """Stream text tokens one chunk at a time, with persisted history."""
    chroma.add_message(conversation_id, "user", message)

    stream = _client.chat.completions.create(
        model=_model,
        max_tokens=16000,
        messages=_build_messages(conversation_id, message),
        stream=True,
    )

    collected = []
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            collected.append(text)
            yield text

    chroma.add_message(conversation_id, "assistant", "".join(collected))
