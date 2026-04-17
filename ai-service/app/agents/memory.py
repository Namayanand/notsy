import logging
from typing import Dict, Any, Optional

from app.agents.base import BaseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """Agent that tracks learning progress and patterns"""

    name = "memory"
    description = "Tracks learning progress and patterns"

    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the memory agent"""
        operation = input.payload.get("operation", "track")

        if operation == "track":
            return await self._track_session(input)
        elif operation == "insights":
            return await self._get_insights(input)
        elif operation == "update_roadmap":
            return await self._update_roadmap(input)
        else:
            return await self._track_session(input)

    async def _track_session(self, input: AgentInput) -> AgentOutput:
        """Track current learning session"""
        current_topic = input.context.get("current_topic")
        active_agent = input.context.get("active_agent")
        duration = input.payload.get("duration", 0)

        if not current_topic:
            from app.core.memory_store import memory_store
            try:
                roadmap = await memory_store.get_session_context(input.session_id, "roadmap")
                index = await memory_store.get_session_context(input.session_id, "current_topic_index") or 0
                if roadmap and isinstance(roadmap, list) and index < len(roadmap):
                    current_topic = roadmap[index].get("name")
            except Exception:
                pass

        logger.info(f"Memory: Tracking session for {current_topic}")

        # Store session in memory
        try:
            await self.execute_tool(
                "store_memory",
                user_id=input.user_id,
                memory_type="session",
                content=f"Studied {current_topic} with {active_agent}",
                metadata={
                    "topic": current_topic,
                    "agent": active_agent,
                    "duration": duration
                }
            )
        except Exception as e:
            logger.warning(f"Could not store session: {e}")

        # Analyze patterns
        patterns = await self._analyze_patterns(input.user_id)

        # Update roadmap progress
        from app.core.memory_store import memory_store
        try:
            roadmap = await memory_store.get_session_context(input.session_id, "roadmap")
            index = await memory_store.get_session_context(input.session_id, "current_topic_index") or 0

            if roadmap and isinstance(roadmap, list) and index < len(roadmap):
                roadmap[index]["status"] = "completed"
                await memory_store.set_session_context(input.session_id, "roadmap", roadmap)
                index += 1
                await memory_store.set_session_context(input.session_id, "current_topic_index", index)

                # Update context with new current topic
                if index < len(roadmap):
                    current_topic = roadmap[index].get("name")
        except Exception as e:
            logger.warning(f"Could not update roadmap: {e}")

        return AgentOutput(
            agent_type=self.name,
            result={
                "patterns": patterns,
                "tracked": True,
                "completed_topic": current_topic
            },
            next_agent="planner",
            metadata={"pattern_count": len(patterns)}
        )

    async def _get_insights(self, input: AgentInput) -> AgentOutput:
        """Generate insights for UI display"""
        logger.info(f"Memory: Generating insights for user {input.user_id}")

        try:
            from app.core.memory_store import memory_store
            insights = await memory_store.get_insights(input.user_id)
        except Exception as e:
            logger.warning(f"Could not get insights: {e}")
            insights = {
                "weak_topics": [],
                "mistake_count": 0,
                "improvement_trend": []
            }

        return AgentOutput(
            agent_type=self.name,
            result={
                "insights": insights
            },
            metadata={}
        )

    async def _update_roadmap(self, input: AgentInput) -> AgentOutput:
        """Update roadmap based on performance"""
        performance_data = input.payload.get("performance_data", {})

        try:
            await self.execute_tool(
                "update_learning_plan",
                user_id=input.user_id,
                roadmap_data=performance_data
            )
        except Exception as e:
            logger.warning(f"Could not update learning plan: {e}")

        return AgentOutput(
            agent_type=self.name,
            result={
                "roadmap_updated": True
            },
            next_agent=None,
            metadata={}
        )

    async def _analyze_patterns(self, user_id: int) -> list:
        """Analyze user learning patterns"""
        try:
            memories = await self.execute_tool(
                "retrieve_memory",
                user_id=user_id,
                query="mistakes weak areas",
                memory_types=["mistake", "assessment"]
            )

            patterns = []
            topic_mistakes = {}

            for mem in memories:
                metadata = mem.get("metadata", {})
                topic = metadata.get("topic", "unknown")
                if topic not in topic_mistakes:
                    topic_mistakes[topic] = 0
                topic_mistakes[topic] += 1

            # Get top weak areas
            sorted_topics = sorted(topic_mistakes.items(), key=lambda x: x[1], reverse=True)
            for topic, count in sorted_topics[:3]:
                patterns.append(f"Struggles with {topic} ({count} mistakes)")

            return patterns
        except Exception as e:
            logger.warning(f"Could not analyze patterns: {e}")
            return []