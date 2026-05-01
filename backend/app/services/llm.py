from typing import AsyncGenerator
import anthropic

_client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Answer questions clearly and concisely."
)

_SYSTEM = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]


async def ask(message: str) -> str:
    """Send a single message and return the complete text response."""
    async with _client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        system=_SYSTEM,
        messages=[{"role": "user", "content": message}],
    ) as stream:
        msg = await stream.get_final_message()

    return next(
        (block.text for block in msg.content if block.type == "text"), ""
    )


async def ask_stream(message: str) -> AsyncGenerator[str, None]:
    """Stream text tokens one chunk at a time."""
    async with _client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        system=_SYSTEM,
        messages=[{"role": "user", "content": message}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
