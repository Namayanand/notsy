import os
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException
import httpx

from app.models.schemas import EmbedResourceRequest, EmbedStatusResponse, EmbedCallbackRequest
from app.core.embeddings import embeddings
from app.core.youtube_loader import is_youtube_url, YouTubeLoader
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter()

SPRING_BOOT_CALLBACK_URL = os.getenv("SPRING_BOOT_CALLBACK_URL", "http://localhost:8080")


async def embed_resource_task(request: EmbedResourceRequest):
    """Background task to embed a resource."""
    resource_id = request.resource_id
    topic_id = request.topic_id
    file_path = request.file_path
    source_url = request.source_url
    file_type = request.file_type
    user_id = request.user_id

    try:
        chunk_count = 0

        # Handle YouTube URLs specially
        if source_url and is_youtube_url(source_url):
            logger.info(f"Processing YouTube URL: {source_url}")
            youtube_data = YouTubeLoader.load(source_url)
            if youtube_data.get("chunks"):
                chunks = youtube_data["chunks"]
                metadatas = [{
                    "source": c["source"],
                    "type": c.get("type", "youtube"),
                    "topic_id": str(topic_id),
                    "user_id": str(user_id)
                } for c in chunks]
                vector_store.add_documents(topic_id, [c["text"] for c in chunks], metadatas)
                chunk_count = len(chunks)
        else:
            # Standard embedding
            chunk_count = embeddings.embed_resource(
                resource_id=resource_id,
                topic_id=topic_id,
                file_path=file_path,
                source_url=source_url,
                file_type=file_type,
                user_id=user_id
            )

        # Notify Spring Boot backend
        await callback_success(resource_id, chunk_count)

    except Exception as e:
        logger.error(f"Error embedding resource {resource_id}: {e}")
        await callback_failure(resource_id, str(e))


async def callback_success(resource_id: int, chunk_count: int):
    """Notify backend of successful embedding."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SPRING_BOOT_CALLBACK_URL}/api/ai/callback",
                json={
                    "resource_id": resource_id,
                    "status": "DONE",
                    "chunk_count": chunk_count
                },
                timeout=10.0
            )
    except Exception as e:
        logger.error(f"Failed to send success callback for resource {resource_id}: {e}")


async def callback_failure(resource_id: int, error_message: str):
    """Notify backend of failed embedding."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SPRING_BOOT_CALLBACK_URL}/api/ai/callback",
                json={
                    "resource_id": resource_id,
                    "status": "FAILED",
                    "error_message": error_message
                },
                timeout=10.0
            )
    except Exception as e:
        logger.error(f"Failed to send failure callback for resource {resource_id}: {e}")


@router.post("")
async def embed_resource(request: EmbedResourceRequest, background_tasks: BackgroundTasks):
    """Trigger async embedding of a resource."""
    background_tasks.add_task(embed_resource_task, request)
    return {
        "status": "processing",
        "resource_id": request.resource_id,
        "message": "Embedding started in background"
    }


@router.delete("/topic/{topic_id}")
async def delete_topic_embeddings(topic_id: int):
    """Delete all embeddings for a topic."""
    result = vector_store.delete_collection(topic_id)
    if result == "deleted":
        return {"status": "deleted", "topic_id": topic_id}
    elif result == "not_found":
        raise HTTPException(status_code=404, detail=f"No embeddings found for topic {topic_id}")
    else:
        raise HTTPException(status_code=500, detail="Failed to delete embeddings")


@router.get("/status/{resource_id}")
async def get_embed_status(resource_id: int):
    """Get embedding status for a resource."""
    # Note: This would need to be tracked separately since ChromaDB doesn't store resource_id
    # For now, return a placeholder
    return {
        "resource_id": resource_id,
        "status": "unknown",
        "message": "Status tracking not implemented - check via backend API"
    }


@router.post("/callback")
async def receive_callback(request: EmbedCallbackRequest):
    """Receive callback from AI service (for internal use)."""
    logger.info(f"Callback received: resource_id={request.resource_id}, status={request.status}")
    return {"status": "received"}
