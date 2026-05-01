import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.repository import save_message
from src.services import (
    get_travel_recommendations,
    get_travel_recommendations_stream,
    save_place_to_list,
    add_message,
    fetch_conversation_history,
    remove_conversation_history,
    fetch_all_conversations,
)
from src.schemas import (
    ChatRequest,
    PlaceRecommendation,
    RecommendationResponse,
    SaveRequest,
    SaveResponse,
    ConversationHistoryResponse,
    DeleteHistoryResponse,
    AllConversationsResponse,
)

# =============================================================================
# Routes
# =============================================================================
router = APIRouter(prefix="/api/v1")

@router.get("/")
def read_root():
    return {
        "message": "AI Travel Matchmaker API v2 is running!",
        "endpoints": {
            "POST /api/v1/recommend": "Get personalized travel recommendations",
            "POST /api/v1/save": "Save a place (returns updated saved list for localStorage)",
        }
    }


@router.post("/recommend", response_model=RecommendationResponse)
def recommend(request: ChatRequest):
    try:
        profile_dict = request.user_profile.model_dump()
        top_places, ai_reason, suggested_prompts = get_travel_recommendations(
            profile_dict=profile_dict,
            message=request.message,
            conversation_id=request.conversation_id,
            nickname=request.nickname,
        )

        if not top_places:
            raise HTTPException(
                status_code=404,
                detail="No places found matching your preferences. Try adjusting your filters!"
            )

        formatted = [
            PlaceRecommendation(
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
            )
            for p in top_places
        ]

        return RecommendationResponse(
            conversation_id=request.conversation_id,
            message=request.message,
            recommendations=formatted,
            ai_reason=ai_reason,
            suggested_prompts=suggested_prompts,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/stream")
def recommend_stream(request: ChatRequest):
    """
    SSE streaming version of /recommend.

    Emits three event types:
      1. {"type": "recommendations", "conversation_id": ..., "message": ...,
          "recommendations": [...], "suggested_prompts": [...]}
      2. {"type": "delta", "content": "<token>"}  — one per LLM chunk
      3. {"type": "done"}
    """
    try:
        profile_dict = request.user_profile.model_dump()
        top_places, suggested_prompts, ai_stream = get_travel_recommendations_stream(
            profile_dict=profile_dict,
            message=request.message,
            conversation_id=request.conversation_id,
            nickname=request.nickname,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not top_places:
        raise HTTPException(
            status_code=404,
            detail="No places found matching your preferences. Try adjusting your filters!",
        )

    formatted = [
        PlaceRecommendation(
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
        )
        for p in top_places
    ]

    def event_stream():
        # Event 1 — send all recommendations up-front
        rec_event = {
            "type": "recommendations",
            "conversation_id": request.conversation_id,
            "message": request.message,
            "recommendations": [p.model_dump() for p in formatted],
            "suggested_prompts": suggested_prompts,
        }
        yield f"data: {json.dumps(rec_event)}\n\n"

        # Events 2…N — stream AI response token by token
        accumulated = []
        for chunk in ai_stream:
            accumulated.append(chunk)
            yield f"data: {json.dumps({'type': 'delta', 'content': chunk})}\n\n"

        # Persist the full assistant reply to history
        if request.conversation_id:
            save_message(request.conversation_id, "assistant", "".join(accumulated))

        # Final event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/save", response_model=SaveResponse)
def save(request: SaveRequest):
    try:
        updated_list, already_saved = save_place_to_list(
            place_name=request.place_name,
            current_saved=request.current_saved,
        )

        if already_saved:
            msg = f"'{request.place_name}' is already in your saved list."
        else:
            msg = f"'{request.place_name}' has been saved to your list!"

        return SaveResponse(
            success=True,
            message=msg,
            updated_saved_location=updated_list,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Chat History Routes
# =============================================================================

@router.get("/history", response_model=AllConversationsResponse)
def get_all_history():
    try:
        return fetch_all_conversations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{conversation_id}", response_model=ConversationHistoryResponse)
def get_history(conversation_id: str):
    try:
        return fetch_conversation_history(conversation_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{conversation_id}", response_model=DeleteHistoryResponse)
def delete_history(conversation_id: str):
    try:
        return remove_conversation_history(conversation_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
