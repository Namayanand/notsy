import logging
from typing import Dict, Any, Optional

from app.agents.base import BaseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class EvaluatorAgent(BaseAgent):
    """Agent that generates and evaluates quizzes"""

    name = "evaluator"
    description = "Generates and evaluates quizzes"

    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the evaluator agent"""
        mode = input.payload.get("mode", "generate")  # generate, evaluate

        # Get current topic
        topic = input.payload.get("topic")
        if not topic:
            topic = input.context.get("current_topic")

        if not topic:
            from app.core.memory_store import memory_store
            try:
                roadmap = await memory_store.get_session_context(input.session_id, "roadmap")
                index = await memory_store.get_session_context(input.session_id, "current_topic_index") or 0
                if roadmap and isinstance(roadmap, list) and index < len(roadmap):
                    topic = roadmap[index].get("name")
            except Exception:
                pass

        if mode == "generate":
            return await self._generate_quiz(input, topic)
        else:
            return await self._evaluate_answer(input, topic)

    async def _generate_quiz(self, input: AgentInput, topic: str) -> AgentOutput:
        """Generate quiz questions"""
        if not topic:
            return AgentOutput(
                agent_type=self.name,
                result={"error": "No topic for quiz generation"},
                next_agent=None,
                metadata={"error": True}
            )

        difficulty = input.payload.get("difficulty", "medium")
        num_questions = input.payload.get("num_questions", 5)

        logger.info(f"Evaluator: Generating quiz for {topic}")

        # Generate quiz using tool
        quiz_result = await self.execute_tool(
            "get_quiz_questions",
            topic=topic,
            difficulty=difficulty,
            num_questions=num_questions
        )

        questions = quiz_result.get("questions", [])

        if not questions:
            # Fallback quiz
            questions = self._create_fallback_quiz(topic)

        # Store questions in context
        from app.core.memory_store import memory_store
        try:
            await memory_store.set_session_context(
                input.session_id,
                "current_quiz",
                questions,
                ttl=3600
            )
        except Exception:
            pass

        return AgentOutput(
            agent_type=self.name,
            result={
                "quiz": questions,
                "topic": topic,
                "mode": "generated"
            },
            next_agent="motivator",
            metadata={"question_count": len(questions), "mode": "generate"}
        )

    async def _evaluate_answer(self, input: AgentInput, topic: str) -> AgentOutput:
        """Evaluate a user's answer"""
        question = input.payload.get("question", "")
        user_answer = input.payload.get("answer", "")
        correct_answer = input.payload.get("correct_answer", "")

        if not question or not user_answer:
            return AgentOutput(
                agent_type=self.name,
                result={"error": "Missing question or answer"},
                next_agent=None,
                metadata={"error": True}
            )

        logger.info(f"Evaluator: Evaluating answer for {topic}")

        # Evaluate using tool
        feedback = await self.execute_tool(
            "evaluate_answer",
            question=question,
            user_answer=user_answer,
            correct_answer=correct_answer,
            topic=topic or "unknown"
        )

        is_correct = feedback.get("is_correct", False)

        # Store mistake in memory if wrong
        if not is_correct:
            try:
                await self.execute_tool(
                    "store_memory",
                    user_id=input.user_id,
                    memory_type="mistake",
                    content=f"Mistake on {topic}: {question} - User answered: {user_answer}",
                    metadata={"topic": topic, "question": question}
                )
            except Exception as e:
                logger.warning(f"Could not store mistake: {e}")

        # Store assessment in memory
        try:
            await self.execute_tool(
                "store_memory",
                user_id=input.user_id,
                memory_type="assessment",
                content=f"Quiz on {topic}: score {feedback.get('score', 0)}%",
                metadata={
                    "topic": topic,
                    "score": feedback.get("score", 0),
                    "is_correct": is_correct
                }
            )
        except Exception as e:
            logger.warning(f"Could not store assessment: {e}")

        return AgentOutput(
            agent_type=self.name,
            result={
                "feedback": feedback,
                "topic": topic,
                "mode": "evaluated"
            },
            next_agent="memory",
            metadata={"is_correct": is_correct, "mode": "evaluate"}
        )

    def _create_fallback_quiz(self, topic: str):
        """Create a basic quiz if AI generation fails"""
        return [
            {
                "question": f"What is a key concept in {topic}?",
                "type": "multiple_choice",
                "options": [
                    "Option A",
                    "Option B",
                    "Option C",
                    "Option D"
                ],
                "correct_answer": "Option A",
                "explanation": "This is the correct answer."
            }
        ]