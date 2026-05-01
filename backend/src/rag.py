"""
RAG (Retrieval-Augmented Generation) Logic
==========================================
v2 — Updated to support:
- message field (user's chat message → AI answers contextually)
- saved_location in profile (boosts similar recommendations)
- favourite field in profile
- conversation_id aware prompts
"""

import chromadb
from chromadb.config import Settings
from langchain_huggingface import HuggingFaceEmbeddings
from src import client as _client

# =============================================================================
# Setup Configuration
# =============================================================================

CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "places_search_index"

client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH,
    settings=Settings(anonymized_telemetry=False)
)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

print("🔄 Loading Embedding Model (BGE-M3)...")
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# =============================================================================
# Step 1: Build Search Query
# =============================================================================

def build_search_query(user_profile: dict, message: str = "") -> str:
    """
    Build a search query combining:
    - user's current message (if any)
    - user preferences (style, food, transportation, region)
    - saved_location (previously liked places → boost similar ones)
    """
    parts = []

    # 1. Include the user's message as primary intent
    if message and message.strip():
        parts.append(f"User is asking: {message.strip()}.")

    # 2. Style preferences
    styles = user_profile.get('style', [])
    if styles:
        parts.append(f"Travel style: {', '.join(styles)}.")

    # 3. Food preferences
    foods = user_profile.get('food', [])
    if foods:
        parts.append(f"Food preferences: {', '.join(foods)}.")

    # 4. Transportation
    transports = user_profile.get('transportation', [])
    if transports:
        parts.append(f"Transportation: {', '.join(transports)}.")

    # 5. Budget
    budget = user_profile.get('budget', '')
    if budget:
        parts.append(f"Budget: {budget}.")

    # 6. Favourite provinces / regions
    provinces = user_profile.get('favourite_province', [])
    if provinces:
        parts.append(f"Preferred provinces: {', '.join(provinces)}.")

    favourite = user_profile.get('favourite', [])
    if favourite:
        parts.append(f"Favourite areas: {', '.join(favourite)}.")

    # 7. 🌟 Saved locations → inject as "I enjoyed these places, find similar ones"
    saved = user_profile.get('saved_location', [])
    if saved:
        parts.append(
            f"User has already saved and enjoyed: {', '.join(saved)}. "
            f"Recommend similar or complementary places."
        )

    return " ".join(parts)


# =============================================================================
# Step 2: Search + Calculate Match Score
# =============================================================================

# Provinces that have actual data in the database
PROVINCES_WITH_DATA = {'Chumphon', 'Ratchaburi', 'Yala', 'Chonburi'}


def get_recommendations(user_profile: dict, message: str = "", top_k: int = 5) -> list:
    """
    Search ChromaDB and calculate Match Score.

    Match Score formula:
    (Similarity * 0.7) + (Hidden_Gem * 0.2) + ((1 - Crowd_Level/10) * 0.1)

    Similarity has the highest weight so that the user's actual query drives
    rankings. Static bias from hidden_gem_score is kept small to avoid the
    same high-scoring places always winning regardless of the query.

    Bonus: +0.05 if place style/tags matches saved_location context
    """
    search_query = build_search_query(user_profile, message)

    # Retrieve top 10 candidates for reranking.
    # When the user has selected provinces that exist in the database, filter
    # the search to those provinces so results are actually relevant.
    query_embedding = embeddings.embed_query(search_query)

    fav_provinces = user_profile.get('favourite_province', [])
    provinces_in_data = [p for p in fav_provinces if p in PROVINCES_WITH_DATA]

    query_kwargs = dict(
        query_embeddings=[query_embedding],
        n_results=10,
        include=["documents", "metadatas", "distances"],
    )
    if provinces_in_data:
        query_kwargs['where'] = {"province": {"$in": provinces_in_data}}

    results = collection.query(**query_kwargs)

    # Build saved_location set for bonus scoring
    saved_locations = set(
        loc.lower() for loc in user_profile.get('saved_location', [])
    )

    candidates = []
    for i in range(len(results['ids'][0])):
        meta = results['metadatas'][0][i]
        doc = results['documents'][0][i]
        dist = results['distances'][0][i]

        # Distance → Similarity (distance range 0–2)
        similarity_score = max(0, 1 - (dist / 2))

        crowd_level = meta.get('crowd_level', 5)
        hidden_gem_score = meta.get('hidden_gem_score', 0.5)
        name_en = meta.get('name_en', '')
        name_th = meta.get('name_th', '')
        place_name = name_en or name_th or meta.get('province', 'Unknown Place')

        # Base match score — similarity has the dominant weight so the user's
        # query drives results rather than static hidden_gem / crowd bias.
        match_score = (
            (similarity_score * 0.7)
            + (hidden_gem_score * 0.2)
            + ((1 - (crowd_level / 10)) * 0.1)
        )

        # 🌟 Saved-location bonus: boost places in same province/style as saved ones
        if saved_locations:
            place_province = meta.get('province', '').lower()
            place_style = meta.get('style', '').lower()
            place_tags = meta.get('tags', '').lower()

            for saved in saved_locations:
                if (
                    saved in place_province
                    or saved in place_style
                    or saved in place_tags
                    or saved in place_name.lower()
                ):
                    match_score = min(1.0, match_score + 0.05)
                    break  # Apply bonus only once per place

        candidates.append({
            "id": meta.get('id'),
            "name": place_name,
            "name_th": name_th,
            "name_en": name_en,
            "province": meta.get('province'),
            "region": meta.get('region'),
            "style": meta.get('style'),
            "budget_range": meta.get('budget_range'),
            "match_score": round(match_score, 4),
            "crowd_level": crowd_level,
            "hidden_gem_score": hidden_gem_score,
            "tags": meta.get('tags'),
            "details": doc,
        })

    # Rerank by match score
    candidates.sort(key=lambda x: x['match_score'], reverse=True)
    return candidates[:top_k]


# =============================================================================
# Step 3: AI Generation — answer message + explain recommendations
# =============================================================================

def _build_system_prompt(user_name: str | None) -> str:
    """
    Build the system prompt for GuidyTH.
    `user_name` is the traveller's display name (for personalisation only).
    The AI persona is always 'GuidyTH' — never pretend to be the user.
    """
    prompt = (
        "You are GuidyTH, a friendly AI travel companion specialising exclusively in "
        "hidden-gem destinations across Thailand. "
        "IMPORTANT RULES:\n"
        "1. You MUST only recommend and discuss places that appear in the "
        "'Recommended places' list provided in the user message. "
        "Do NOT mention, suggest, or describe any place that is NOT in that list, "
        "even if you know about it from your general knowledge.\n"
        "2. If the user asks about a place or region that is not covered by the "
        "provided list, politely say you can only help with the places in your "
        "current database and offer to suggest one of the provided places instead.\n"
        "3. Keep answers short, natural, and conversational — 3–4 sentences max. "
        "Always respond in English."
    )
    # Personalise with the user's name only when it looks like a real name
    # (not an anonymous UUID such as 'user_abc123').
    if user_name and not user_name.startswith('user_'):
        prompt += (
            f"\nThe traveller's name is {user_name}. "
            "Address them by name occasionally to make the conversation feel warm and personal."
        )
    return prompt


def generate_ai_reasons(places: list, user_profile: dict, message: str = "", nickname: str | None = None) -> str:
    """
    Send top places + user message to Groq (LLaMA 3.3).
    AI will:
    1. Answer the user's specific message/question (if any)
    2. Explain why these places match the user's profile
    Responds in English (app is for international tourists).
    """
    places_context = ""
    for idx, p in enumerate(places):
        places_context += (
            f"{idx+1}. {p['name']} (Match: {p['match_score']*100:.1f}%)\n"
            f"   Thai Name: {p.get('name_th', 'N/A')}\n"
            f"   Province: {p.get('province', 'N/A')} | Region: {p.get('region', 'N/A')}\n"
            f"   Style: {p.get('style', 'N/A')} | Budget: {p.get('budget_range', 'N/A')}\n"
            f"   Crowd Level: {p.get('crowd_level', 'N/A')}/10 "
            f"| Hidden Gem Score: {p.get('hidden_gem_score', 'N/A')}\n"
            f"   Tags: {p.get('tags', 'N/A')}\n"
            f"   Details: {p['details'][:300]}...\n\n"
        )

    # Mention saved places for context
    saved = user_profile.get('saved_location', [])
    saved_context = ""
    if saved:
        saved_context = (
            f"\nUser has already saved these places: {', '.join(saved)}. "
            "Do NOT re-recommend these. Focus on new discoveries."
        )

    system_prompt = _build_system_prompt(nickname)

    user_prompt = (
        f"User's message: \"{message}\"\n\n"
        f"User profile: {user_profile}\n"
        f"{saved_context}\n\n"
        f"Recommended places (ONLY use these — do NOT mention any other destinations):\n{places_context}\n"
        "Using ONLY the places listed above, answer the user's question and explain why "
        "these places are a great fit for them. "
        "Do not recommend or describe any place not in the list above. "
        "Keep it to 3–4 sentences max, friendly and natural."
    )

    print("🤖 Asking Groq (LLaMA 3.3) to generate response...")
    try:
        chat_completion = _client.groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="typhoon-v2.5-30b-a3b-instruct",
            temperature=0.3,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Sorry, something went wrong while generating a response: {str(e)}"


def generate_ai_reasons_stream(places: list, user_profile: dict, message: str = "", nickname: str | None = None):
    """
    Same as generate_ai_reasons but streams token-by-token via SSE.
    Yields text chunks as they arrive from the LLM.
    """
    places_context = ""
    for idx, p in enumerate(places):
        places_context += (
            f"{idx+1}. {p['name']} (Match: {p['match_score']*100:.1f}%)\n"
            f"   Thai Name: {p.get('name_th', 'N/A')}\n"
            f"   Province: {p.get('province', 'N/A')} | Region: {p.get('region', 'N/A')}\n"
            f"   Style: {p.get('style', 'N/A')} | Budget: {p.get('budget_range', 'N/A')}\n"
            f"   Crowd Level: {p.get('crowd_level', 'N/A')}/10 "
            f"| Hidden Gem Score: {p.get('hidden_gem_score', 'N/A')}\n"
            f"   Tags: {p.get('tags', 'N/A')}\n"
            f"   Details: {p['details'][:300]}...\n\n"
        )

    saved = user_profile.get('saved_location', [])
    saved_context = ""
    if saved:
        saved_context = (
            f"\nUser has already saved these places: {', '.join(saved)}. "
            "Do NOT re-recommend these. Focus on new discoveries."
        )

    system_prompt = _build_system_prompt(nickname)

    user_prompt = (
        f"User's message: \"{message}\"\n\n"
        f"User profile: {user_profile}\n"
        f"{saved_context}\n\n"
        f"Recommended places (ONLY use these — do NOT mention any other destinations):\n{places_context}\n"
        "Using ONLY the places listed above, answer the user's question and explain why "
        "these places are a great fit for them. "
        "Do not recommend or describe any place not in the list above. "
        "Keep it to 3–4 sentences max, friendly and natural."
    )

    print("🤖 Streaming response from LLM...")
    try:
        stream = _client.groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="typhoon-v2.5-30b-a3b-instruct",
            temperature=0.3,
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        yield f"Sorry, something went wrong while generating a response: {str(e)}"


# =============================================================================
# Step 4: Generate Suggested Follow-up Prompts
# =============================================================================

def generate_suggested_prompts(places: list, user_profile: dict) -> list:
    """
    Generate follow-up prompt buttons based on top recommended place.
    Follow-up province prompts use the user's favourite_province when available
    so suggestions stay relevant to the user's selected regions.
    """
    if not places:
        return []

    top_place = places[0]
    name = top_place.get('name', 'this place')
    rec_province = top_place.get('province', 'this province')
    budget = user_profile.get('budget', 'low')

    # Use user's preferred province for generic follow-ups; fall back to the
    # recommended place's province only when no preference is set.
    fav_provinces = user_profile.get('favourite_province', [])
    explore_province = fav_provinces[0] if fav_provinces else rec_province

    prompts = [
        f"How do I get to {name}?",
        f"What are the best local foods near {explore_province}?",
        f"Show me more hidden gems in {explore_province}.",
        f"Is {name} good for a {budget} budget trip?",
        f"Save {name} to my list",           # → frontend detects "Save … to my list"
        "That's all, thanks! 😊",            # → จบการสนทนา
    ]

    return prompts


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    mock_profile = {
        'favourite_province': ['Chumphon'],
        'favourite': [],
        'style': ['nature', 'quiet'],
        'food': ['seafood'],
        'transportation': ['boat'],
        'budget': 'low',
        'avoid_crowd': True,
        'saved_location': [],  # empty on first visit
    }
    mock_message = "I want somewhere quiet, not too crowded"

    print("\n🔍 Searching with message + profile...")
    top_places = get_recommendations(mock_profile, message=mock_message, top_k=3)

    print("\n🏆 Top Matches:")
    for p in top_places:
        print(f"  - {p['name']} | Score: {p['match_score']} | Province: {p['province']}")

    print("\n💬 Generating AI response...")
    ai_response = generate_ai_reasons(top_places, mock_profile, mock_message)
    print("\n✨ AI:", ai_response)

    print("\n💡 Suggested Prompts:")
    for prompt in generate_suggested_prompts(top_places, mock_profile):
        print(f"  → {prompt}")
