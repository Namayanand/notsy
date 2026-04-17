import logging
from typing import Dict, Any, Optional

from app.agents.base import BaseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class TutorAgent(BaseAgent):
    """Agent that explains concepts with adaptive depth"""

    name = "tutor"
    description = "Explains concepts with adaptive depth"

    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the tutor agent"""
        topic = input.payload.get("topic")
        topic_id = input.payload.get("topic_id")
        user_level = input.context.get("user_level", "intermediate")
        learning_mode = input.context.get("learning_mode", "MASTER_THIS")

        if not topic:
            # Get current topic from roadmap
            from app.core.memory_store import memory_store
            try:
                roadmap = await memory_store.get_session_context(input.session_id, "roadmap")
                index = await memory_store.get_session_context(input.session_id, "current_topic_index") or 0

                if roadmap and isinstance(roadmap, list) and index < len(roadmap):
                    topic = roadmap[index].get("name")
            except Exception:
                pass

        if not topic:
            return AgentOutput(
                agent_type=self.name,
                result={"error": "No topic provided and no current topic in context"},
                next_agent=None,
                metadata={"error": True}
            )

        logger.info(f"Tutor: Explaining topic: {topic}")

        # Get user's understanding level from memory
        try:
            understanding = await self.execute_tool(
                "retrieve_memory",
                user_id=input.user_id,
                query=f"understanding of {topic}",
                memory_types=["assessment"]
            )
        except Exception:
            understanding = []

        # Determine explanation depth based on user's history
        depth = self._determine_depth(understanding, user_level)

        # Get relevant notes if topic_id provided
        context = ""
        if topic_id:
            try:
                notes_result = await self.execute_tool(
                    "search_notes",
                    query=f"explain {topic}",
                    topic_id=topic_id,
                    n_results=3
                )
                documents = notes_result.get("documents", [])
                if documents and documents[0]:
                    context = "\n\n".join(documents)
            except Exception as e:
                logger.warning(f"Could not search notes: {e}")

        # Generate explanation using tool
        explanation_result = await self.execute_tool(
            "explain_concept",
            topic=topic,
            depth=depth,
            context=context
        )

        explanation = explanation_result.get("explanation", "Could not generate explanation")

        # Store explanation in context
        from app.core.memory_store import memory_store
        try:
            await memory_store.set_session_context(
                input.session_id,
                "current_explanation",
                explanation,
                ttl=3600
            )
        except Exception:
            pass

        return AgentOutput(
            agent_type=self.name,
            result={
                "explanation": explanation,
                "topic": topic,
                "depth": depth,
                "has_sources": bool(context)
            },
            next_agent="evaluator",
            metadata={"depth": depth}
        )

    def _determine_depth(self, understanding: list, user_level: str) -> str:
        """Determine explanation depth based on user's understanding"""
        if not understanding or len(understanding) == 0:
            return "medium"

        # Check recent assessment scores
        try:
            for mem in understanding[:5]:
                metadata = mem.get("metadata", {})
                score = metadata.get("score", 100)
                if score < 50:
                    return "eli5"  # Need simpler explanation
                elif score < 70:
                    return "medium"
        except Exception:
            pass

        # Use user's stated level
        level_map = {"beginner": "eli5", "intermediate": "medium", "advanced": "deep"}
        return level_map.get(user_level, "medium")