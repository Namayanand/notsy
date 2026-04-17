import os
import logging
from typing import Dict, Callable, Any, List, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for agent tools"""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str):
        """Decorator to register a tool"""
        def decorator(func: Callable):
            self._tools[name] = func
            logger.info(f"Registered tool: {name}")
            return func
        return decorator

    async def execute(self, name: str, **kwargs) -> Any:
        """Execute a registered tool"""
        if name not in self._tools:
            logger.warning(f"Tool {name} not found")
            return {"error": f"Tool {name} not found"}
        try:
            return await self._tools[name](**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return {"error": str(e)}

    def list_tools(self) -> List[str]:
        """List all registered tools"""
        return list(self._tools.keys())


tools = ToolRegistry()


# Tool implementations
@tools.register("search_notes")
async def search_notes(query: str, topic_id: int, n_results: int = 5):
    """Search notes using vector store"""
    from app.services.vector_store import vector_store
    try:
        results = vector_store.query(topic_id, query, n_results=n_results)
        return results
    except Exception as e:
        logger.error(f"Error searching notes: {e}")
        return {"documents": [], "metadatas": [], "distances": []}


@tools.register("semantic_search")
async def semantic_search(query: str, notebook_id: Optional[int] = None,
                         user_id: Optional[int] = None, n_results: int = 10):
    """Perform semantic search across user's content"""
    from app.services.vector_store import vector_store
    try:
        if notebook_id:
            results = vector_store.semantic_search(query, n_results=n_results,
                                                    notebook_id=notebook_id)
        else:
            results = vector_store.global_search(query, n_results=n_results)
        return results
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return {"documents": [], "metadatas": [], "distances": []}


@tools.register("store_memory")
async def store_memory(user_id: int, memory_type: str, content: str,
                      metadata: Optional[Dict[str, Any]] = None):
    """Store a memory entry in long-term memory"""
    from app.core.memory_store import memory_store
    try:
        result = await memory_store.write(user_id, memory_type, content, metadata or {})
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        return {"success": False, "error": str(e)}


@tools.register("retrieve_memory")
async def retrieve_memory(user_id: int, query: str,
                          memory_types: Optional[List[str]] = None):
    """Retrieve memories from long-term memory"""
    from app.core.memory_store import memory_store
    try:
        results = await memory_store.read(user_id, query, memory_types)
        return results
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}")
        return []


@tools.register("get_streak_data")
async def get_streak_data(user_id: int, topic_id: Optional[int] = None):
    """Get user streak data from backend"""
    import requests
    try:
        url = os.getenv("BACKEND_URL", "http://localhost:8080")
        endpoint = f"{url}/api/streaks"
        if topic_id:
            endpoint += f"/topic/{topic_id}"
        else:
            endpoint += "/global"

        response = requests.get(endpoint, timeout=5)
        if response.status_code == 200:
            return response.json().get("data", {})
        return {"currentStreak": 0, "longestStreak": 0}
    except Exception as e:
        logger.error(f"Error getting streak data: {e}")
        return {"currentStreak": 0, "longestStreak": 0}


@tools.register("update_learning_plan")
async def update_learning_plan(user_id: int, roadmap_data: Dict[str, Any]):
    """Update the user's learning plan based on performance"""
    from app.core.memory_store import memory_store
    try:
        # Store updated roadmap
        await memory_store.set_session_context(
            f"user_{user_id}",
            "roadmap",
            roadmap_data
        )
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating learning plan: {e}")
        return {"success": False, "error": str(e)}


@tools.register("get_quiz_questions")
async def get_quiz_questions(topic: str, difficulty: str = "medium",
                            num_questions: int = 5):
    """Generate quiz questions using AI"""
    from app.core.rag_engine import rag_engine
    try:
        prompt = f"""Generate {num_questions} quiz questions about "{topic}" at {difficulty} difficulty.

Format as a JSON array with this structure:
[{{
  "question": "question text",
  "type": "multiple_choice|short_answer",
  "options": ["option1", "option2", "option3", "option4"],
  "correct_answer": "option1",
  "explanation": "why this is correct"
}}]

Return ONLY the JSON array, no additional text."""

        client = rag_engine._get_client()
        response = client.chat.completions.create(
            model=rag_engine.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        # Try to parse as JSON
        try:
            questions = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                questions = json.loads(match.group())
            else:
                questions = []

        return {"questions": questions, "topic": topic, "difficulty": difficulty}
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        return {"questions": [], "error": str(e)}


@tools.register("evaluate_answer")
async def evaluate_answer(question: str, user_answer: str,
                          correct_answer: str, topic: str):
    """Evaluate a user's answer and provide feedback"""
    from app.core.rag_engine import rag_engine
    try:
        prompt = f"""Evaluate the user's answer to this question:

Question: {question}
User's Answer: {user_answer}
Correct Answer: {correct_answer}

Provide feedback in JSON format:
{{
  "is_correct": true/false,
  "score": 0-100,
  "feedback": "explanation of why the answer is right/wrong",
  "suggestion": "what the user should study next"
}}"""

        client = rag_engine._get_client()
        response = client.chat.completions.create(
            model=rag_engine.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500
        )

        content = response.choices[0].message.content
        try:
            feedback = json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                feedback = json.loads(match.group())
            else:
                feedback = {"is_correct": False, "score": 0, "feedback": "Could not evaluate", "suggestion": ""}

        return feedback
    except Exception as e:
        logger.error(f"Error evaluating answer: {e}")
        return {"is_correct": False, "score": 0, "error": str(e)}


@tools.register("get_weak_topics")
async def get_weak_topics(user_id: int):
    """Retrieve user's weak topics from memory"""
    from app.core.memory_store import memory_store
    try:
        memories = await memory_store.read(
            user_id,
            "mistakes weak areas performance",
            memory_types=["mistake", "assessment"]
        )

        weak_topics = []
        for mem in memories:
            metadata = mem.get("metadata", {})
            if "topic" in metadata:
                weak_topics.append(metadata["topic"])

        # Count occurrences
        from collections import Counter
        topic_counts = Counter(weak_topics)
        top_weak = [topic for topic, count in topic_counts.most_common(5)]

        return {"weak_topics": top_weak}
    except Exception as e:
        logger.error(f"Error getting weak topics: {e}")
        return {"weak_topics": []}


@tools.register("generate_motivation")
async def generate_motivation(streak_data: Dict[str, Any],
                             performance_data: Optional[Dict[str, Any]] = None):
    """Generate a personalized motivational message"""
    from app.core.rag_engine import rag_engine

    current_streak = streak_data.get("currentStreak", 0)
    longest_streak = streak_data.get("longestStreak", 0)

    prompt = f"""Generate a short, encouraging motivational message for a student.

Current streak: {current_streak} days
Longest streak: {longest_streak} days
Recent performance: {performance_data}

Keep it brief (2-3 sentences), warm, and motivating. No emoji."""

    try:
        client = rag_engine._get_client()
        response = client.chat.completions.create(
            model=rag_engine.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150
        )

        message = response.choices[0].message.content.strip()
        return {"message": message, "streak": current_streak}
    except Exception as e:
        logger.error(f"Error generating motivation: {e}")
        return {"message": "Keep up the great work!", "streak": current_streak}


@tools.register("generate_roadmap")
async def generate_roadmap(goal: str, current_topics: List[str],
                          weak_topics: List[str],
                          performance_history: Optional[List[Dict]] = None):
    """Generate a learning roadmap using AI"""
    from app.core.rag_engine import rag_engine

    history_text = ""
    if performance_history:
        history_text = "\n".join([f"- {h.get('topic', '')}: {h.get('score', 0)}%"
                                  for h in performance_history[:10]])

    prompt = f"""Create a learning roadmap for: {goal}

Current topics being studied: {current_topics}
Areas needing improvement: {weak_topics}
Recent performance:
{history_text}

Generate a structured roadmap as a JSON array with this structure:
[{{
  "id": "topic_1",
  "name": "topic name",
  "difficulty": 1-5,
  "duration_hours": float,
  "prerequisites": ["prerequisite_topic_id"],
  "status": "pending"
}}]

Return ONLY the JSON array, no additional text. Include 5-8 topics in logical order."""

    try:
        client = rag_engine._get_client()
        response = client.chat.completions.create(
            model=rag_engine.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        content = response.choices[0].message.content
        try:
            roadmap = json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                roadmap = json.loads(match.group())
            else:
                roadmap = []

        return {"roadmap": roadmap, "goal": goal}
    except Exception as e:
        logger.error(f"Error generating roadmap: {e}")
        return {"roadmap": [], "error": str(e)}


@tools.register("explain_concept")
async def explain_concept(topic: str, depth: str = "medium",
                          context: Optional[str] = None):
    """Generate an explanation of a concept"""
    from app.core.rag_engine import rag_engine

    depth_instruction = {
        "eli5": "Explain in simple terms, like teaching a 5-year-old. Use analogies.",
        "medium": "Explain at an intermediate level with clear examples.",
        "deep": "Explain in depth with technical details and edge cases."
    }.get(depth, "Explain at an intermediate level with clear examples.")

    prompt = f"""Explain the concept of "{topic}". {depth_instruction}

Context from notes:
{context or 'No specific context provided.'}

Provide a clear, structured explanation with examples."""

    try:
        client = rag_engine._get_client()
        response = client.chat.completions.create(
            model=rag_engine.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500
        )

        explanation = response.choices[0].message.content
        return {"explanation": explanation, "topic": topic, "depth": depth}
    except Exception as e:
        logger.error(f"Error explaining concept: {e}")
        return {"explanation": "Sorry, I couldn't generate an explanation.", "error": str(e)}