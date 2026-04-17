import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

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

        result = await rag_engine.chat(
            topic_id=request.topic_id,
            message=request.message,
            history=history,
            learning_mode=request.learning_mode,
            use_web_search=getattr(request, 'use_web_search', False),
            explain_depth=getattr(request, 'explain_depth', None),
            system_prompt=getattr(request, 'system_prompt', None),
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


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response token by token."""
    try:
        history = [{"role": msg.role, "content": msg.content} for msg in request.history]

        async def event_generator():
            async for chunk in rag_engine.chat_stream(
                topic_id=request.topic_id,
                message=request.message,
                history=history,
                learning_mode=request.learning_mode,
                use_web_search=getattr(request, 'use_web_search', False),
                explain_depth=getattr(request, 'explain_depth', None),
                system_prompt=getattr(request, 'system_prompt', None),
            ):
                yield f"data: {json.dumps(chunk)}\n\n".encode()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except Exception as e:
        logger.error(f"Error in streaming chat endpoint: {e}")
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n".encode()]),
            media_type="text/event-stream"
        )
