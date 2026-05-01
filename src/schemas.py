from pydantic import BaseModel
from typing import List, Optional


class UserProfile(BaseModel):
    favourite: List[str] = []
    favourite_province: List[str] = []
    style: List[str] = []
    food: List[str] = []
    transportation: List[str] = []
    budget: str = "mid"
    avoid_crowd: bool = False
    saved_location: List[str] = []


class ChatRequest(BaseModel):
    message: str = ""
    conversation_id: Optional[str] = None
    user_profile: UserProfile = UserProfile()


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
    message: str
    recommendations: List[PlaceRecommendation]
    ai_reason: str
    suggested_prompts: List[str] = []


class SaveRequest(BaseModel):
    conversation_id: Optional[str] = None
    place_id: str
    place_name: str
    current_saved: List[str] = []


class SaveResponse(BaseModel):
    success: bool
    message: str
    updated_saved_location: List[str]


# =============================================================================
# Chat History Schemas
# =============================================================================

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    timestamp: float


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    message_count: int
    messages: List[MessageOut]


class DeleteHistoryResponse(BaseModel):
    conversation_id: str
    deleted_count: int
    success: bool


class AllConversationsResponse(BaseModel):
    total_conversations: int
    conversations: List[ConversationHistoryResponse]
