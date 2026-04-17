import logging
import json
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from app.core.study_planner import study_planner

logger = logging.getLogger(__name__)

router = APIRouter()


class StudyPlannerRequest(BaseModel):
    prompt: str
    plan_id: Optional[int] = None
    user_id: Optional[int] = None
    topics: Optional[List[dict]] = None
    quiz_history: Optional[dict] = None
    days_available: Optional[int] = None
    exam_date: Optional[str] = None
    hours_per_day: Optional[float] = 2.0
    user_preference: Optional[str] = "balanced"


class MultiAgentStudyPlannerRequest(BaseModel):
    topics: List[dict]
    quiz_history: dict = {}
    days_available: int
    exam_date: str
    hours_per_day: float = 2.0
    user_preference: str = "balanced"


@router.post("/multi_agent/study_planner")
async def multi_agent_study_planner(request: MultiAgentStudyPlannerRequest):
    """3-agent orchestration: Retrieval -> Evaluator -> Planner."""
    try:
        result = await study_planner.create_study_plan(
            topics=request.topics,
            quiz_history=request.quiz_history,
            days_available=request.days_available,
            exam_date=request.exam_date,
            hours_per_day=request.hours_per_day,
            user_preference=request.user_preference
        )
        return result
    except Exception as e:
        logger.error(f"Study planner error: {e}")
        return {"error": str(e), "schedule": []}


@router.post("/generate_flashcards")
async def generate_flashcards(request: dict):
    """Generate flashcards from conversation context."""
    try:
        from app.core.rag_engine import rag_engine

        conversation_context = request.get("prompt", "")
        topic_id = request.get("topic_id")

        prompt = f"""Generate 5-10 smart flashcards from the following study material or conversation.
Create varied cards: basic Q&A, multiple choice, definitions, and short answer.

Content:
{conversation_context}

Respond ONLY with a JSON array (no markdown).
Format: [{{"front": "question", "back": "answer", "type": "BASIC|MULTIPLE_CHOICE|DEFINITION|SHORT_ANSWER"}}]"""

        client = rag_engine._get_client()
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        # Strip markdown code blocks if present
        if content.strip().startswith("```"):
            content = content.strip()[7:]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
            if content.endswith("```"):
                content = content[:-3].strip()

        flashcards = json.loads(content)
        return {"flashcards": flashcards, "topic_id": topic_id}

    except json.JSONDecodeError as e:
        logger.error(f"Flashcard generation parse error: {e}")
        return {"flashcards": [], "error": str(e)}
    except Exception as e:
        logger.error(f"Flashcard generation error: {e}")
        return {"flashcards": [], "error": str(e)}


@router.post("/generate_quiz")
async def generate_quiz(request: dict):
    """Generate quiz questions from topic content."""
    try:
        from app.core.rag_engine import rag_engine

        topic_title = request.get("topic_title", "")
        topic_description = request.get("topic_description", "")
        quiz_type = request.get("quiz_type", "MIXED")
        difficulty_tier = request.get("difficulty_tier", 2)
        question_count = request.get("question_count", 10)

        difficulty_instruction = {
            1: "Make questions easy - basic recall and simple concepts.",
            2: "Make questions medium difficulty - application and understanding.",
            3: "Make questions hard - analysis, synthesis, and edge cases."
        }.get(difficulty_tier, "Make questions medium difficulty.")

        type_instruction = {
            "MCQ": "Generate ONLY multiple choice questions with 4 options each.",
            "SHORT_ANSWER": "Generate ONLY short answer questions.",
            "DEFINITION_RECALL": "Generate ONLY definition recall questions.",
            "MIXED": "Generate a mix of MCQ, short answer, and definition questions."
        }.get(quiz_type, "Generate a mix of question types.")

        prompt = f"""Generate {question_count} quiz questions about: {topic_title}.
{topic_description}

{difficulty_instruction}
{type_instruction}

For MCQ: Include 4 options (A, B, C, D). Mark the correct answer.
For short answer: Just provide the question, answer is evaluated by exact match.
For definition: Provide a term, student defines it.

Respond ONLY with a JSON array (no markdown).
Format MCQ: [{{"type": "MCQ", "question": "...", "answer": "B", "options": ["A: ...", "B: ...", "C: ...", "D: ..."], "area": "topic area"}}]
Format short answer: [{{"type": "SHORT_ANSWER", "question": "...", "answer": "...", "area": "..."}}]
Format definition: [{{"type": "DEFINITION", "term": "...", "definition": "..."}}]"""

        client = rag_engine._get_client()
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )

        content = response.choices[0].message.content
        if content.strip().startswith("```"):
            content = content.strip()[7:]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
            if content.endswith("```"):
                content = content[:-3].strip()

        questions = json.loads(content)

        # Standardize format
        standardized = []
        for q in questions:
            standardized.append({
                "type": q.get("type", "MCQ"),
                "question": q.get("question", q.get("term", "")),
                "answer": q.get("answer", q.get("definition", "")),
                "options": q.get("options", []),
                "area": q.get("area", topic_title)
            })

        return {"questions": standardized}

    except json.JSONDecodeError as e:
        logger.error(f"Quiz generation parse error: {e}")
        return {"questions": [], "error": str(e)}
    except Exception as e:
        logger.error(f"Quiz generation error: {e}")
        return {"questions": [], "error": str(e)}
