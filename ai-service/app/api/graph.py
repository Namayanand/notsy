import logging
from fastapi import APIRouter

from app.models.schemas import GenerateGraphRequest, GenerateGraphResponse, TopicData
from app.core.graph_builder import graph_builder

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/graph/generate", response_model=GenerateGraphResponse)
async def generate_graph(request: GenerateGraphRequest):
    """Generate knowledge graph relations for topics."""
    try:
        topics = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description
            }
            for t in request.topics
        ]

        relations = await graph_builder.generate_knowledge_graph(topics)

        return GenerateGraphResponse(relations=relations)

    except Exception as e:
        logger.error(f"Error generating graph: {e}")
        return GenerateGraphResponse(relations=[])
