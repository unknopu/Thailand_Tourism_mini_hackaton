"""
RAG (Retrieval-Augmented Generation) Logic
==========================================
v4 — Updated to fix:
- Bug: Do NOT recommend places that are already in the saved_location list.
- Keep the bonus scoring logic for places in the same area/style.
"""

import os
import chromadb
from chromadb.config import Settings
from langchain_huggingface import HuggingFaceEmbeddings
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Setup Configuration
# =============================================================================

CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "places_search_index"

client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH,
    settings=Settings(anonymized_telemetry=False)
)
collection = client.get_collection(name=COLLECTION_NAME)

print("🔄 Loading Embedding Model (BGE-M3)...")
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# =============================================================================
# Step 1: Build Search Query
# =============================================================================

def build_search_query(user_profile: dict, message: str = "") -> str:
    parts = []

    if message and message.strip():
        parts.append(f"User is asking: {message.strip()}.")

    styles = user_profile.get('style', [])
    if styles:
        parts.append(f"Travel style: {', '.join(styles)}.")

    foods = user_profile.get('food', [])
    if foods:
        parts.append(f"Food preferences: {', '.join(foods)}.")

    transports = user_profile.get('transportation', [])
    if transports:
        parts.append(f"Transportation: {', '.join(transports)}.")

    budget = user_profile.get('budget', '')
    if budget:
        parts.append(f"Budget: {budget}.")

    provinces = user_profile.get('favourite_province', [])
    if provinces:
        parts.append(f"Preferred provinces: {', '.join(provinces)}.")

    favourite = user_profile.get('favourite', [])
    if favourite:
        parts.append(f"Favourite areas: {', '.join(favourite)}.")

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

def get_recommendations(user_profile: dict, message: str = "", top_k: int = 3) -> list:
    """
    Search ChromaDB and calculate Match Score.
    """
    search_query = build_search_query(user_profile, message)

    query_embedding = embeddings.embed_query(search_query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=15, # ดึงมาเผื่อไว้กรองออก
        include=["documents", "metadatas", "distances"]
    )

    # แปลงชื่อสถานที่ใน saved_location เป็นตัวพิมพ์เล็กทั้งหมดเพื่อใช้ตอนกรอง
    saved_locations = set(
        loc.lower() for loc in user_profile.get('saved_location', [])
    )

    candidates = []
    for i in range(len(results['ids'][0])):
        meta = results['metadatas'][0][i]
        doc = results['documents'][0][i]
        dist = results['distances'][0][i]

        similarity_score = max(0, 1 - (dist / 2))

        crowd_level = meta.get('crowd_level', 5)
        hidden_gem_score = meta.get('hidden_gem_score', 0.5)
        name_en = meta.get('name_en', '')
        name_th = meta.get('name_th', '')
        place_name = name_en or name_th or meta.get('province', 'Unknown Place')

        match_score = (
            (similarity_score * 0.5)
            + (hidden_gem_score * 0.3)
            + ((1 - (crowd_level / 10)) * 0.2)
        )

        # ให้คะแนน Bonus ถ้าคล้ายกับสถานที่ที่ Save ไว้
        if saved_locations:
            place_province = meta.get('province', '').lower()
            place_style = meta.get('style', '').lower()
            place_tags = meta.get('tags', '').lower()

            for saved in saved_locations:
                if (
                    saved in place_province
                    or saved in place_style
                    or saved in place_tags
                ):
                    match_score = min(1.0, match_score + 0.05)
                    break 

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

    # เรียงลำดับตามคะแนน
    candidates.sort(key=lambda x: x['match_score'], reverse=True)

    # 🌟 FILTER: กรองสถานที่ที่อยู่ใน saved_location ออก 🌟
    filtered_candidates = []
    for c in candidates:
        place_name_lower = c['name'].lower()
        name_en_lower = c['name_en'].lower()
        
        # เช็คว่าชื่อสถานที่นี้ (ไม่ว่าจะภาษาไทยหรืออังกฤษ) อยู่ในเซ็ต saved_locations หรือไม่
        if place_name_lower not in saved_locations and name_en_lower not in saved_locations:
            filtered_candidates.append(c)
            
    # คืนค่าเฉพาะจำนวนที่ต้องการ
    return filtered_candidates[:top_k]


# =============================================================================
# Step 3: AI Generation
# =============================================================================

def generate_ai_reasons(places: list, user_profile: dict, message: str = "") -> str:
    if not places:
        return "Sorry, I couldn't find any new places matching your criteria."

    places_context = ""
    for idx, p in enumerate(places):
        places_context += (
            f"{idx+1}. {p['name']} (Match: {p['match_score']*100:.1f}%)\n"
            f"   Province: {p.get('province', 'N/A')} | Style: {p.get('style', 'N/A')}\n"
            f"   Details: {p['details'][:200]}...\n\n"
        )

    saved = user_profile.get('saved_location', [])
    saved_context = ""
    if saved:
        saved_context = (
            f"\nUser has already saved these places: {', '.join(saved)}. "
        )

    system_prompt = (
        "You are a friendly and knowledgeable Thailand travel guide. "
        "Always respond in English. Keep answers short, natural, and conversational. "
        "Answer the user's question first, then explain why the recommended places fit."
    )

    user_prompt = (
        f"User's message: \"{message}\"\n\n"
        f"User profile: {user_profile}\n"
        f"{saved_context}\n\n"
        f"Recommended places (these are NEW places, not saved ones):\n{places_context}\n"
        "Explain why these new places are a great fit. "
        "Keep it to 3–4 sentences max, friendly and natural."
    )

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Sorry, something went wrong while generating a response."


# =============================================================================
# Step 4: Generate Suggested Follow-up Prompts
# =============================================================================

def generate_suggested_prompts(places: list, user_profile: dict) -> list:
    if not places:
        return []

    top_place = places[0]
    name = top_place.get('name', 'this place')
    province = top_place.get('province', 'this area')
    budget = user_profile.get('budget', 'low')

    prompts = [
        f"How do I get to {name}?",
        f"What are the best local foods near {province}?",
        f"Show me more hidden gems in {province}.",
        f"Is {name} good for a {budget} budget trip?",
        "Save this place to my list",        
        "That's all, thanks! 😊",            
    ]

    return prompts