import logging
from typing import Dict, Any, Optional

from app.agents.base import BaseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Agent that creates learning roadmaps based on user goals"""

    name = "planner"
    description = "Creates learning roadmaps based on user goals"

    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the planner agent"""
        user_goal = input.payload.get("goal", "")
        current_topics = input.context.get("current_topics", [])
        weak_topics = input.context.get("weak_topics", [])

        if not user_goal:
            return AgentOutput(
                agent_type=self.name,
                result={"error": "No goal provided"},
                next_agent=None,
                metadata={"error": True}
            )

        logger.info(f"Planner: Creating roadmap for goal: {user_goal}")

        # Get performance history from memory to inform planning
        try:
            performance_history = await self.execute_tool(
                "retrieve_memory",
                user_id=input.user_id,
                query=f"performance on {user_goal}",
                memory_types=["mistake", "assessment"]
            )
        except Exception as e:
            logger.warning(f"Could not retrieve performance history: {e}")
            performance_history = []

        # Get weak topics
        try:
            weak_data = await self.execute_tool("get_weak_topics", user_id=input.user_id)
            weak_topics = weak_data.get("weak_topics", weak_topics)
        except Exception as e:
            logger.warning(f"Could not get weak topics: {e}")

        # Generate roadmap using tool
        roadmap_result = await self.execute_tool(
            "generate_roadmap",
            goal=user_goal,
            current_topics=current_topics,
            weak_topics=weak_topics,
            performance_history=performance_history[:5] if isinstance(performance_history, list) else None
        )

        roadmap = roadmap_result.get("roadmap", [])

        if not roadmap:
            # Fallback: create a basic roadmap
            roadmap = self._create_fallback_roadmap(user_goal)

        # Store roadmap in session context
        from app.core.memory_store import memory_store
        try:
            await memory_store.set_session_context(
                input.session_id,
                "roadmap",
                roadmap,
                ttl=7200
            )
            await memory_store.set_session_context(
                input.session_id,
                "current_topic_index",
                0,
                ttl=7200
            )
        except Exception as e:
            logger.warning(f"Could not store roadmap: {e}")

        return AgentOutput(
            agent_type=self.name,
            result={
                "roadmap": roadmap,
                "goal": user_goal,
                "topic_count": len(roadmap)
            },
            next_agent="retriever",
            metadata={"topic_count": len(roadmap)}
        )

    def _create_fallback_roadmap(self, goal: str):
        """Create a basic roadmap if AI generation fails"""
        return [
            {
                "id": "topic_1",
                "name": f"Introduction to {goal}",
                "difficulty": 1,
                "duration_hours": 1.0,
                "prerequisites": [],
                "status": "pending"
            },
            {
                "id": "topic_2",
                "name": f"Core concepts of {goal}",
                "difficulty": 2,
                "duration_hours": 2.0,
                "prerequisites": ["topic_1"],
                "status": "pending"
            },
            {
                "id": "topic_3",
                "name": f"Advanced {goal}",
                "difficulty": 3,
                "duration_hours": 3.0,
                "prerequisites": ["topic_2"],
                "status": "pending"
            },
            {
                "id": "topic_4",
                "name": f"Practice and review",
                "difficulty": 2,
                "duration_hours": 1.5,
                "prerequisites": ["topic_3"],
                "status": "pending"
            }
        ]