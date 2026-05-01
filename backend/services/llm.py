from typing import AsyncGenerator
from openai import OpenAI

from repositories import chroma

_client: OpenAI | None = None
_model: str = "typhoon-v2.5-30b-a3b-instruct"

SYSTEM_PROMPT = (
    """
    คุณคือเจ้าหน้าที่ผู้เชี่ยวชาญด้านการให้คำแนะนำการท่องเที่ยว โดยจะอ้างอิงจากข้อมูลพื้นฐาน (background) ของผู้ถามเพื่อวิเคราะห์และให้คำแนะนำที่สั้น กระชับ และได้ใจความ
    หากข้อมูลไม่เพียงพอ ให้สอบถามข้อมูลเพิ่มเติมก่อนตอบ
    คำตอบในแต่ละครั้งต้องประกอบด้วย:
    1. จังหวัดและชื่อสถานที่
    2. เหตุผลที่แนะนำ
    3. เนื้อหาเพิ่มเติม
    คำตอบทั้งหมดต้องมีความยาวไม่เกิน 120 คำ

    You are a travel recommendation expert. Use the user's background information to generate concise and meaningful travel suggestions.
    If the information is insufficient, ask follow-up questions before answering.
    Each response must include:
    1. Province and place name
    2. Reason for recommendation
    3. Additional details
    The total response must not exceed 120 words.
    """
)


def init_client(api_key: str, base_url: str) -> None:
    global _client
    print(f"[*] llm configurated")
    _client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )


def _build_user_profile_prompt(user_profile: dict) -> str:
    parts = []
    if user_profile.get("favourite_province"):
        parts.append(f"Favourite provinces: {', '.join(user_profile['favourite_province'])}")
    if user_profile.get("style"):
        parts.append(f"Travel style: {', '.join(user_profile['style'])}")
    if user_profile.get("food"):
        parts.append(f"Food preferences: {', '.join(user_profile['food'])}")
    if user_profile.get("transportation"):
        parts.append(f"Preferred transportation: {', '.join(user_profile['transportation'])}")
    return "\n".join(parts)


def _build_messages(conversation_id: str, new_message: str, user_profile: dict | None = None) -> list[dict]:
    """Build the full message list: system prompt + user profile + history + new user message."""
    history = chroma.get_recent_messages(conversation_id, limit=20)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if user_profile:
        profile_text = _build_user_profile_prompt(user_profile)
        if profile_text:
            messages.append({"role": "system", "content": f"User profile:\n{profile_text}"})
    for entry in history:
        messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": new_message})
    return messages


async def ask(message: str, conversation_id: str = "default", user_profile: dict | None = None) -> str:
    """Send a message and return the complete text response, with persisted history."""
    chroma.add_message(conversation_id, "user", message)

    response = _client.chat.completions.create(
        model=_model,
        max_tokens=8000,
        messages=_build_messages(conversation_id, message, user_profile),
    )

    assistant_message = response.choices[0].message.content or ""
    chroma.add_message(conversation_id, "assistant", assistant_message)
    return assistant_message


async def ask_stream(message: str, conversation_id: str = "default", user_profile: dict | None = None) -> AsyncGenerator[str, None]:
    """Stream text tokens one chunk at a time, with persisted history."""
    chroma.add_message(conversation_id, "user", message)

    stream = _client.chat.completions.create(
        model=_model,
        max_tokens=16000,
        messages=_build_messages(conversation_id, message, user_profile),
        stream=True,
    )

    collected = []
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            collected.append(text)
            yield text

    chroma.add_message(conversation_id, "assistant", "".join(collected))
