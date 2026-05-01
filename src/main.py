"""
FastAPI Main Application — v2
==============================
รองรับ:
- ChatRequest schema ใหม่ (message + conversation_id + user_profile)
- user_profile มี favourite, saved_location เพิ่มมา
- POST /recommend  → ค้นหา + ตอบ message
- POST /save       → บันทึกสถานที่ (ส่ง saved_location กลับให้ frontend update localStorage)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from src.rag import get_recommendations, generate_ai_reasons, generate_suggested_prompts

app = FastAPI(title="AI Travel Matchmaker API", version="2.0")

# =============================================================================
# CORS
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request / Response Schemas
# =============================================================================

class UserProfile(BaseModel):
    favourite: List[str] = []              # favourite areas (general)
    favourite_province: List[str] = []     # preferred provinces
    style: List[str] = []                  # travel style
    food: List[str] = []                   # food preferences
    transportation: List[str] = []         # transportation mode
    budget: str = "mid"
    avoid_crowd: bool = False
    saved_location: List[str] = []         # 🌟 places user has saved (from localStorage)


class ChatRequest(BaseModel):
    """
    Schema ที่ frontend ส่งมา — ตรงกับที่เพื่อนวางไว้
    {
        "message": "อาหารไรอร่อยสุด",
        "conversation_id": "88",
        "user_profile": { ... }
    }
    """
    message: str = ""
    conversation_id: Optional[str] = None
    user_profile: UserProfile = UserProfile()
    conversation_history: List[dict] = [] 


class PlaceRecommendation(BaseModel):
    id: str
    name: str
    name_th: str = ""
    name_en: str = ""
    province: str = ""
    region: str = ""
    style: str = ""
    budget_range: str = ""
    match_score: float
    crowd_level: int
    hidden_gem_score: float
    tags: str = ""


class RecommendationResponse(BaseModel):
    conversation_id: Optional[str]
    message: str                           # original message echoed back
    recommendations: List[PlaceRecommendation]
    ai_reason: str                         # AI response in Thai
    suggested_prompts: List[str] = []
    assistant_message: str = ""   #  เพิ่ม — ให้ frontend เก็บลง history


# =============================================================================
# Save Feature Schema
# =============================================================================

class SaveRequest(BaseModel):
    """
    Frontend ส่งมาเมื่อ user กดบันทึกสถานที่
    Backend คืน updated saved_location list ให้ frontend เก็บใน localStorage
    """
    conversation_id: Optional[str] = None
    place_id: str
    place_name: str                        # ชื่อสถานที่ (ใช้ใน saved_location list)
    current_saved: List[str] = []          # saved_location ปัจจุบันจาก localStorage


class SaveResponse(BaseModel):
    success: bool
    message: str
    updated_saved_location: List[str]      # ส่งกลับให้ frontend อัปเดต localStorage


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/")
def read_root():
    return {
        "message": "🚀 AI Travel Matchmaker API v2 is running!",
        "endpoints": {
            "POST /recommend": "Get personalized travel recommendations",
            "POST /save": "Save a place (returns updated saved list for localStorage)",
        }
    }


@app.post("/recommend", response_model=RecommendationResponse)
def get_travel_recommendations(request: ChatRequest):
    """
    Main recommendation endpoint.

    Flow:
    1. รับ message + conversation_id + user_profile (มี saved_location ด้วย)
    2. ค้นหาสถานที่จาก ChromaDB โดยใช้ message + profile
    3. Boost สถานที่ที่คล้าย saved_location
    4. AI ตอบ message เป็นภาษาไทย + อธิบาย recommendation
    5. ส่ง suggested_prompts กลับให้ frontend ทำเป็นปุ่ม
    """
    try:
        profile_dict = request.user_profile.model_dump()

        # Get recommendations (message-aware + saved_location boosted)
        top_places = get_recommendations(
            user_profile=profile_dict,
            message=request.message,
            top_k=3
        )

        if not top_places:
            raise HTTPException(
                status_code=404,
                detail="No places found matching your preferences. Try adjusting your filters!"
            )

        # Generate AI response (Thai)
        ai_explanation = generate_ai_reasons(
            places=top_places,
            user_profile=profile_dict,
            message=request.message,
            conversation_history=request.conversation_history  #
        )

        # Generate follow-up prompt buttons
        suggested_prompts = generate_suggested_prompts(top_places, profile_dict)

        # Format recommendations
        formatted = []
        for p in top_places:
            formatted.append(PlaceRecommendation(
                id=p.get('id', ''),
                name=p.get('name', 'Unknown Place'),
                name_th=p.get('name_th', ''),
                name_en=p.get('name_en', ''),
                province=p.get('province', ''),
                region=p.get('region', ''),
                style=p.get('style', ''),
                budget_range=p.get('budget_range', ''),
                match_score=p.get('match_score', 0.0),
                crowd_level=p.get('crowd_level', 5),
                hidden_gem_score=p.get('hidden_gem_score', 0.5),
                tags=p.get('tags', ''),
            ))

        return RecommendationResponse(
            conversation_id=request.conversation_id,
            message=request.message,
            recommendations=formatted,
            ai_reason=ai_explanation,
            assistant_message=ai_explanation,
            suggested_prompts=suggested_prompts,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save", response_model=SaveResponse)
def save_place(request: SaveRequest):
    """
    Save a place to the user's saved list.

    Flow:
    1. รับ place_name + current_saved (จาก localStorage)
    2. เพิ่ม place_name เข้า list (ถ้ายังไม่มี)
    3. ส่ง updated list กลับ → frontend เก็บลง localStorage
       แล้วส่งมาใน user_profile.saved_location ใน request ถัดไป

    ไม่ต้องมี DB — frontend เป็น source of truth
    """
    try:
        current = list(request.current_saved)

        if request.place_name not in current:
            current.append(request.place_name)
            saved = True
            msg = f"'{request.place_name}' has been saved to your list! 📍"
        else:
            saved = True
            msg = f"'{request.place_name}' is already in your saved list."

        return SaveResponse(
            success=saved,
            message=msg,
            updated_saved_location=current,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
