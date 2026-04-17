import logging
from typing import Dict, Any, Optional

from app.agents.base import BaseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class MotivatorAgent(BaseAgent):
    """Agent that generates motivation and tracks streaks"""

    name = "motivator"
    description = "Generates motivation and tracks streaks"

    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the motivator agent"""
        operation = input.payload.get("operation", "motivate")

        # Get streak data
        streak_data = await self._get_streak_data(input.user_id)

        if operation == "motivate":
            return await self._generate_motivation(input, streak_data)
        elif operation == "nudge":
            return await self._generate_nudge(input, streak_data)
        else:
            return await self._generate_motivation(input, streak_data)

    async def _generate_motivation(self, input: AgentInput, streak_data: Dict) -> AgentOutput:
        """Generate personalized motivation"""
        logger.info(f"Motivator: Generating motivation for user {input.user_id}")

        # Get recent performance for personalized message
        try:
            recent_performance = await self.execute_tool(
                "retrieve_memory",
                user_id=input.user_id,
                query="recent quiz performance",
                memory_types=["mistake", "assessment"]
            )

            # Extract performance data
            perf_data = []
            for mem in recent_performance[:5]:
                metadata = mem.get("metadata", {})
                if metadata:
                    perf_data.append({
                        "topic": metadata.get("topic"),
                        "score": metadata.get("score", 0)
                    })
        except Exception as e:
            logger.warning(f"Could not get recent performance: {e}")
            perf_data = []

        # Generate motivation using tool
        message_result = await self.execute_tool(
            "generate_motivation",
            streak_data=streak_data,
            performance_data=perf_data
        )

        message = message_result.get("message", "Keep up the great work!")
        current_streak = message_result.get("streak", 0)

        # Store motivation in session context
        from app.core.memory_store import memory_store
        try:
            await memory_store.set_session_context(
                input.session_id,
                "motivation",
                message,
                ttl=3600
            )
        except Exception:
            pass

        return AgentOutput(
            agent_type=self.name,
            result={
                "message": message,
                "streak": current_streak,
                "longest_streak": streak_data.get("longestStreak", 0)
            },
            metadata={"message_type": "motivation"}
        )

    async def _generate_nudge(self, input: AgentInput, streak_data: Dict) -> AgentOutput:
        """Generate reminder for weak areas"""
        logger.info(f"Motivator: Generating nudge for user {input.user_id}")

        # Get weak topics
        weak_data = await self.execute_tool("get_weak_topics", user_id=input.user_id)
        weak_topics = weak_data.get("weak_topics", [])

        current_streak = streak_data.get("currentStreak", 0)

        # Build nudge message
        if weak_topics:
            nudge = f"Time to review: {', '.join(weak_topics[:3])}"
        else:
            nudge = "Keep your streak going! Study today."

        if current_streak > 0:
            nudge += f" You're on a {current_streak}-day streak!"

        return AgentOutput(
            agent_type=self.name,
            result={
                "nudge": nudge,
                "streak": current_streak,
                "weak_topics": weak_topics
            },
            metadata={"message_type": "nudge"}
        )

    async def _get_streak_data(self, user_id: int) -> Dict:
        """Get user streak data"""
        try:
            streak_data = await self.execute_tool("get_streak_data", user_id=user_id)
            return streak_data or {"currentStreak": 0, "longestStreak": 0}
        except Exception as e:
            logger.warning(f"Could not get streak data: {e}")
            return {"currentStreak": 0, "longestStreak": 0}