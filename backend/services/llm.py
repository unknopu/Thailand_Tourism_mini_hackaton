from typing import AsyncGenerator
# from openai import AsyncOpenAI
from openai import OpenAI

_client: OpenAI | None = None
_model: str = "typhoon-v2.5-30b-a3b-instruct"


def init_client(api_key: str, base_url: str) -> None:
    global _client
    print(f"[*] llm configurated")
    _client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Answer questions clearly and concisely."
)


async def ask(message: str) -> str:
    """Send a single message and return the complete text response."""
    response = _client.chat.completions.create(
        model=_model,
        max_tokens=8000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )
    return response.choices[0].message.content or ""


async def ask_stream(message: str) -> AsyncGenerator[str, None]:
    """Stream text tokens one chunk at a time."""
    stream = _client.chat.completions.create(
        model=_model,
        max_tokens=16000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        stream=True,
    )
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            yield text
