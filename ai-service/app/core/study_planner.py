import os
import json
import logging
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)


class StudyPlannerAgent:
    """
    Multi-agent study planner that orchestrates 3 agents:
    1. Retrieval Agent - maps topics and estimates coverage depth
    2. Evaluator Agent - pulls quiz history, scores weak spots
    3. Planner Agent - weighs complexity, weak spots, time; outputs schedule
    """

    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self.model = "llama3-70b-8192"

    def _get_client(self):
        if self.client is None:
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY environment variable is not set")
            self.client = Groq(api_key=self.groq_api_key)
        return self.client

    async def create_study_plan(
        self,
        topics: List[Dict[str, Any]],
        quiz_history: Dict[str, Any],
        days_available: int,
        exam_date: str,
        hours_per_day: float = 2.0,
        user_preference: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Create a personalized study plan using 3-agent orchestration.

        Args:
            topics: List of topic dicts with id, title, description
            quiz_history: Dict with weak areas per topic
            days_available: Number of days until exam
            exam_date: Exam date as string
            hours_per_day: Preferred study hours per day
            user_preference: easy, balanced, or hard

        Returns:
            Dict with schedule, analysis, and recommendations
        """
        try:
            # Step 1: Retrieval Agent - assess topic coverage
            coverage_analysis = await self._retrieval_agent(topics)

            # Step 2: Evaluator Agent - identify weak spots
            weak_spots = await self._evaluator_agent(topics, quiz_history, coverage_analysis)

            # Step 3: Planner Agent - create day-by-day schedule
            schedule = await self._planner_agent(
                topics, coverage_analysis, weak_spots,
                days_available, exam_date, hours_per_day, user_preference
            )

            return {
                "coverage_analysis": coverage_analysis,
                "weak_spots": weak_spots,
                "schedule": schedule,
                "exam_date": exam_date,
                "days_available": days_available
            }

        except Exception as e:
            logger.error(f"Study planner error: {e}")
            return {"error": str(e), "schedule": []}

    async def _retrieval_agent(self, topics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Agent 1: Assess coverage depth for each topic."""

        topics_summary = "\n".join([
            f"- {t.get('id')}: {t.get('title')} - {t.get('description', 'No description')}"
            for t in topics
        ])

        prompt = f"""As the Retrieval Agent, analyze these topics and estimate how well-covered they are
in a typical study curriculum. Respond ONLY with a JSON object (no markdown).

For each topic, estimate:
- estimated_hours: How many hours to cover it properly (1-10)
- complexity: easy, medium, or hard
- prerequisites: list of topic IDs that should be studied first
- coverage_depth: How thoroughly it needs to be covered (shallow, medium, deep)

Topics:
{topics_summary}

Return JSON: {{"topics": [{{"id": ..., "estimated_hours": ..., "complexity": "...", "prerequisites": [...], "coverage_depth": "..."}}]}}"""

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except json.JSONDecodeError:
            logger.error("Retrieval agent failed to parse JSON")
            return {"topics": []}

    async def _evaluator_agent(
        self,
        topics: List[Dict[str, Any]],
        quiz_history: Dict[str, Any],
        coverage: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Agent 2: Identify weak spots from quiz history."""

        weak_areas = quiz_history.get("weak_areas", [])
        topics_summary = "\n".join([t.get("title", "") for t in topics])

        prompt = f"""As the Evaluator Agent, identify the weakest areas that need the most study time.

Given:
- Quiz history weak areas: {weak_areas}
- Topics to study: {topics_summary}
- Coverage analysis: {coverage}

Identify the top 3-5 topics or sub-areas that need the MOST study time.
Respond ONLY with a JSON array.

Format: [{{"area": "topic name", "weakness_score": 0.0-1.0, "reason": "why it's weak"}}]"""

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            logger.error("Evaluator agent failed to parse JSON")
            return []

    async def _planner_agent(
        self,
        topics: List[Dict[str, Any]],
        coverage: Dict[str, Any],
        weak_spots: List[Dict[str, Any]],
        days_available: int,
        exam_date: str,
        hours_per_day: float,
        user_preference: str
    ) -> List[Dict[str, Any]]:
        """Agent 3: Create a day-by-day study schedule."""

        topics_json = json.dumps(topics)
        coverage_json = json.dumps(coverage)
        weak_spots_json = json.dumps(weak_spots)

        effort_multiplier = {"easy": 1.3, "balanced": 1.0, "hard": 0.7}.get(user_preference, 1.0)
        adjusted_hours = hours_per_day * effort_multiplier

        prompt = f"""As the Planner Agent, create a day-by-day study schedule.

Context:
- Days available: {days_available}
- Exam date: {exam_date}
- Hours per day available: {adjusted_hours} (adjusted for {user_preference} preference)
- Total topics to cover: {len(topics)}

Topics: {topics_json}
Coverage analysis: {coverage_json}
Weak spots (study these more): {weak_spots_json}

Create a schedule allocating topics to each day. More hours should go to weak spots
and high-complexity topics. Include breaks and review days.

Respond ONLY with a JSON array (no markdown).
Format: [{{"day": 1, "date": "YYYY-MM-DD", "focus": "main topic(s) for today", "topics": [...], "hours": 2.0, "notes": "optional tip"}}]

IMPORTANT: Ensure all {days_available} days are covered, with lighter review days near the end."""

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=3000
            )
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            logger.error("Planner agent failed to parse JSON")
            return []


# Global instance
study_planner = StudyPlannerAgent()
