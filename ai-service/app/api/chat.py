import logging
from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.core.rag_engine import rag_engine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message using RAG."""
    try:
        # Convert ChatMessage objects to dicts for the RAG engine
        history = [{"role": msg.role, "content": msg.content} for msg in request.history]

        result = rag_engine.chat(
            topic_id=request.topic_id,
            message=request.message,
            history=history,
            learning_mode=request.learning_mode
        )

        return ChatResponse(
            response=result["response"],
            sources=result["sources"],
            tokens_used=result["tokens_used"]
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return ChatResponse(
            response="I apologize, but I encountered an error processing your request. Please try again.",
            sources=[],
            tokens_used=0
        )


@router.get("/health")
async def health_check():
    """Check if the AI service is healthy."""
    groq_ok = rag_engine.check_health()
    return {
        "status": "healthy" if groq_ok else "degraded",
        "groq_api": "connected" if groq_ok else "disconnected"
    }
