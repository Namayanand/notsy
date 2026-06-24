"""
LangChain-based Agent Framework for NOTSY
Uses LangChain's AgentExecutor and tool calling capabilities
"""
import os
import json
import logging
from json import JSONDecodeError, JSONDecoder
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime


def _extract_first_json(text: str):
    """
    Extract the first valid JSON value (object or array) from *text* using
    JSONDecoder.raw_decode — avoids the greedy `re.search(r'\\[.*\\]', …, re.DOTALL)`
    pitfall that swallows sibling JSON objects.
    Returns the parsed value, or raises JSONDecodeError if nothing is found.
    """
    decoder = JSONDecoder()
    for i, ch in enumerate(text):
        if ch in ('{', '['):
            try:
                obj, _ = decoder.raw_decode(text, i)
                return obj
            except JSONDecodeError:
                continue
    raise JSONDecodeError("No JSON object or array found", text, 0)

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool, BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.agent import AgentExecutor
from langchain.agents import create_openai_functions_agent, create_structured_chat_agent
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.services.vector_store import vector_store
from app.core.memory_store import memory_store
from app.core.rag_engine import rag_engine

logger = logging.getLogger(__name__)


# ============= LLM Setup =============

def get_groq_llm(temperature: float = 0.3, model: str = None) -> ChatGroq:
    """Get configured Groq LLM instance"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not set")

    model = model or "llama-3.3-70b-versatile"
    return ChatGroq(client=None, api_key=groq_api_key, model=model, temperature=temperature)


# ============= Tool Definitions =============

class SearchNotesInput(BaseModel):
    query: str = Field(description="The search query")
    topic_id: int = Field(description="ID of the topic to search in")
    n_results: int = Field(default=5, description="Number of results to return")


@tool(args_schema=SearchNotesInput)
async def search_notes(query: str, topic_id: int, n_results: int = 5) -> Dict[str, Any]:
    """Search notes using vector store for a specific topic"""
    try:
        results = vector_store.query(topic_id, query, n_results=n_results)
        return results
    except Exception as e:
        logger.error(f"Error searching notes: {e}")
        return {"documents": [], "metadatas": [], "distances": [], "error": str(e)}


class SemanticSearchInput(BaseModel):
    query: str = Field(description="The search query")
    notebook_id: Optional[int] = Field(default=None, description="ID of notebook to search in")
    user_id: Optional[int] = Field(default=None, description="ID of user")
    n_results: int = Field(default=10, description="Number of results to return")


@tool(args_schema=SemanticSearchInput)
async def semantic_search(query: str, notebook_id: Optional[int] = None,
                         user_id: Optional[int] = None, n_results: int = 10) -> Dict[str, Any]:
    """Perform semantic search across user's content"""
    try:
        if notebook_id:
            results = vector_store.semantic_search(query, n_results=n_results, notebook_id=notebook_id)
        else:
            results = vector_store.global_search(query, n_results=n_results)
        return results
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return {"documents": [], "metadatas": [], "distances": [], "error": str(e)}


class StoreMemoryInput(BaseModel):
    user_id: int = Field(description="ID of the user")
    memory_type: str = Field(description="Type of memory (session, mistake, assessment)")
    content: str = Field(description="Content to store")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


@tool(args_schema=StoreMemoryInput)
async def store_memory(user_id: int, memory_type: str, content: str,
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Store a memory entry in long-term memory"""
    try:
        result = await memory_store.write(user_id, memory_type, content, metadata or {})
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        return {"success": False, "error": str(e)}


class RetrieveMemoryInput(BaseModel):
    user_id: int = Field(description="ID of the user")
    query: str = Field(description="Search query for memory")
    memory_types: Optional[List[str]] = Field(default=None, description="Types of memories to search")


@tool(args_schema=RetrieveMemoryInput)
async def retrieve_memory(user_id: int, query: str,
                         memory_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Retrieve memories from long-term memory"""
    try:
        results = await memory_store.read(user_id, query, memory_types)
        return results
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}")
        return []


class GetStreakDataInput(BaseModel):
    user_id: int = Field(description="ID of the user")
    topic_id: Optional[int] = Field(default=None, description="Optional topic ID")


@tool(args_schema=GetStreakDataInput)
async def get_streak_data(user_id: int, topic_id: Optional[int] = None) -> Dict[str, Any]:
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


class GetWeakTopicsInput(BaseModel):
    user_id: int = Field(description="ID of the user")


@tool(args_schema=GetWeakTopicsInput)
async def get_weak_topics(user_id: int) -> Dict[str, Any]:
    """Retrieve user's weak topics from memory"""
    try:
        memories = await memory_store.read(user_id, "mistakes weak areas performance",
                                           memory_types=["mistake", "assessment"])

        weak_topics = []
        for mem in memories:
            metadata = mem.get("metadata", {})
            if "topic" in metadata:
                weak_topics.append(metadata["topic"])

        from collections import Counter
        topic_counts = Counter(weak_topics)
        top_weak = [topic for topic, count in topic_counts.most_common(5)]

        return {"weak_topics": top_weak}
    except Exception as e:
        logger.error(f"Error getting weak topics: {e}")
        return {"weak_topics": []}


class GenerateQuizInput(BaseModel):
    topic: str = Field(description="Topic for quiz")
    difficulty: str = Field(default="medium", description="Difficulty level")
    num_questions: int = Field(default=5, description="Number of questions")


@tool(args_schema=GenerateQuizInput)
async def generate_quiz(topic: str, difficulty: str = "medium",
                       num_questions: int = 5) -> Dict[str, Any]:
    """Generate quiz questions for a topic"""
    from app.core.rag_engine import rag_engine

    prompt = f"""Generate {num_questions} quiz questions about "{topic}" at {difficulty} difficulty.

Format as a JSON array with this structure:
[{{
  "question": "question text",
  "type": "multiple_choice",
  "options": ["option1", "option2", "option3", "option4"],
  "correct_answer": "option1",
  "explanation": "why this is correct"
}}]

Return ONLY the JSON array, no additional text."""

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
            questions = json.loads(content)
        except json.JSONDecodeError:
            try:
                questions = _extract_first_json(content)
            except json.JSONDecodeError:
                questions = []

        return {"questions": questions, "topic": topic, "difficulty": difficulty}
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        return {"questions": [], "error": str(e)}


class EvaluateAnswerInput(BaseModel):
    question: str = Field(description="The quiz question")
    user_answer: str = Field(description="User's answer")
    correct_answer: str = Field(description="Correct answer")
    topic: str = Field(description="Topic of the question")


@tool(args_schema=EvaluateAnswerInput)
async def evaluate_answer(question: str, user_answer: str,
                         correct_answer: str, topic: str) -> Dict[str, Any]:
    """Evaluate a user's quiz answer"""
    from app.core.rag_engine import rag_engine

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

    try:
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
            try:
                feedback = _extract_first_json(content)
            except json.JSONDecodeError:
                feedback = {"is_correct": False, "score": 0, "feedback": "Could not evaluate"}

        return feedback
    except Exception as e:
        logger.error(f"Error evaluating answer: {e}")
        return {"is_correct": False, "score": 0, "error": str(e)}


class GenerateRoadmapInput(BaseModel):
    goal: str = Field(description="Learning goal")
    weak_topics: Optional[List[str]] = Field(default=None, description="Weak topics to address")
    performance_history: Optional[List[Dict]] = Field(default=None, description="Recent performance")


@tool(args_schema=GenerateRoadmapInput)
async def generate_roadmap(goal: str, weak_topics: Optional[List[str]] = None,
                          performance_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Generate a learning roadmap using AI"""
    from app.core.rag_engine import rag_engine

    history_text = ""
    if performance_history:
        history_text = "\n".join([f"- {h.get('topic', '')}: {h.get('score', 0)}%"
                                  for h in performance_history[:10]])

    prompt = f"""Create a learning roadmap for: {goal}

Areas needing improvement: {weak_topics or []}
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
            try:
                roadmap = _extract_first_json(content)
            except json.JSONDecodeError:
                roadmap = []

        return {"roadmap": roadmap, "goal": goal}
    except Exception as e:
        logger.error(f"Error generating roadmap: {e}")
        return {"roadmap": [], "error": str(e)}


class ExplainConceptInput(BaseModel):
    topic: str = Field(description="Topic to explain")
    depth: str = Field(default="medium", description="Explanation depth (eli5, medium, deep)")
    context: Optional[str] = Field(default=None, description="Optional context from notes")


@tool(args_schema=ExplainConceptInput)
async def explain_concept(topic: str, depth: str = "medium",
                          context: Optional[str] = None) -> Dict[str, Any]:
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


class GenerateMotivationInput(BaseModel):
    streak_data: Dict[str, Any] = Field(description="Streak data")
    performance_data: Optional[List[Dict]] = Field(default=None, description="Recent performance")


@tool(args_schema=GenerateMotivationInput)
async def generate_motivation(streak_data: Dict[str, Any],
                              performance_data: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Generate a personalized motivational message"""
    from app.core.rag_engine import rag_engine

    current_streak = streak_data.get("currentStreak", 0)
    longest_streak = streak_data.get("longestStreak", 0)

    prompt = f"""Generate a short, encouraging motivational message for a student.

Current streak: {current_streak} days
Longest streak: {longest_streak} days
Recent performance: {performance_data}

Keep it brief (2-3 sentences), warm, and motivating."""

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


class SummariseConceptsInput(BaseModel):
    topics: List[Dict[str, Any]] = Field(description="Topics covered in the learning session")
    explanations: Optional[List[Dict[str, Any]]] = Field(default=None, description="Explanations generated")
    quiz_results: Optional[List[Dict[str, Any]]] = Field(default=None, description="Quiz results for each topic")


@tool(args_schema=SummariseConceptsInput)
async def summarise_concepts(topics: List[Dict[str, Any]],
                             explanations: Optional[List[Dict[str, Any]]] = None,
                             quiz_results: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Generate a summary of key concepts after learning completion"""
    from app.core.rag_engine import rag_engine

    # Extract topic names
    topic_names = []
    for t in topics:
        if isinstance(t, dict):
            topic_names.append(t.get("name", str(t)))
        elif isinstance(t, str):
            topic_names.append(t)

    if not topic_names:
        return {"summary": "No topics to summarize", "key_takeaways": []}

    quiz_text = ""
    if quiz_results:
        quiz_lines = []
        for r in quiz_results:
            topic = r.get("topic", "unknown")
            score = r.get("score", 0)
            quiz_lines.append(f"- {topic}: {score}%")
        quiz_text = "\nQuiz performance:\n" + "\n".join(quiz_lines)

    # Extract explanation content
    explanation_texts = []
    if explanations:
        for exp in explanations:
            if isinstance(exp, dict) and "content" in exp:
                content = exp["content"]
                if len(content) > 500:
                    content = content[:500] + "..."
                explanation_texts.append(content)

    context_text = "\n\n".join(explanation_texts[:3]) if explanation_texts else "No detailed explanations available."

    prompt = f"""Generate a comprehensive summary of the learning session covering these topics: {', '.join(topic_names)}

{quiz_text}

Key explanations from the session:
{context_text}

Generate a summary with:
1. A brief overview of what was learned
2. 3-5 key takeaways (bullet points)
3. Suggestions for next steps or further learning

Keep it concise and actionable. Format as JSON:
{{
  "summary": "overall summary text",
  "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
  "next_steps": ["suggestion 1", "suggestion 2"]
}}"""

    try:
        client = rag_engine._get_client()
        response = client.chat.completions.create(
            model=rag_engine.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )

        content = response.choices[0].message.content

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            try:
                result = _extract_first_json(content)
            except json.JSONDecodeError:
                result = {"summary": content, "key_takeaways": [], "next_steps": []}

        return result
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return {
            "summary": f"You have completed learning: {', '.join(topic_names)}",
            "key_takeaways": topic_names,
            "next_steps": ["Review the material regularly", "Practice with quizzes"]
        }


# ============= Tool List =============

all_tools = [
    search_notes,
    semantic_search,
    store_memory,
    retrieve_memory,
    get_streak_data,
    get_weak_topics,
    generate_quiz,
    evaluate_answer,
    generate_roadmap,
    explain_concept,
    summarise_concepts,
]


# ============= Agent Creation =============

def create_learning_agent() -> AgentExecutor:
    """Create a LangChain agent for learning workflows"""
    llm = get_groq_llm(temperature=0.3)

    # System prompt for learning agent
    system_prompt = """You are an AI learning assistant that helps users learn effectively.

You have access to tools that can:
- Search and retrieve study materials
- Generate learning roadmaps
- Create explanations at different depth levels
- Generate and evaluate quizzes
- Track learning progress and memories
- Provide motivation

Always use the appropriate tool to help the user. Use clear, educational language."""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        HumanMessage(content="{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    # Create agent
    agent = create_openai_functions_agent(llm, all_tools, prompt)
    executor = AgentExecutor(agent=agent, tools=all_tools, verbose=True)

    return executor


def create_tutor_agent() -> AgentExecutor:
    """Create a specialized tutor agent"""
    llm = get_groq_llm(temperature=0.3)

    system_prompt = """You are an expert tutor who explains concepts clearly.

You can use these tools:
- search_notes: Find relevant study materials
- semantic_search: Search across all content
- explain_concept: Generate explanations at various depth levels (eli5, medium, deep)
- retrieve_memory: Check user's learning history to personalize explanations

Always tailor your explanation depth to the user's demonstrated understanding level."""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content="{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    tutor_tools = [search_notes, semantic_search, explain_concept, retrieve_memory]
    agent = create_openai_functions_agent(llm, tutor_tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tutor_tools, verbose=True)

    return executor


def create_evaluator_agent() -> AgentExecutor:
    """Create a quiz and evaluation agent"""
    llm = get_groq_llm(temperature=0.2)

    system_prompt = """You are a quiz and assessment agent.

You can use these tools:
- generate_quiz: Create quiz questions for a topic
- evaluate_answer: Evaluate user's answers with feedback
- store_memory: Record assessment results
- retrieve_memory: Check past performance

Generate appropriate quizzes and provide constructive feedback on answers."""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content="{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    eval_tools = [generate_quiz, evaluate_answer, store_memory, retrieve_memory]
    agent = create_openai_functions_agent(llm, eval_tools, prompt)
    executor = AgentExecutor(agent=agent, tools=eval_tools, verbose=True)

    return executor


def create_planner_agent() -> AgentExecutor:
    """Create a learning roadmap planner agent"""
    llm = get_groq_llm(temperature=0.3)

    system_prompt = """You are a learning planner that creates personalized roadmaps.

You can use these tools:
- generate_roadmap: Create a structured learning path
- get_weak_topics: Identify areas needing improvement
- retrieve_memory: Check performance history
- store_memory: Save the generated roadmap

Create roadmaps that address the user's goals and weak areas."""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content="{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    plan_tools = [generate_roadmap, get_weak_topics, retrieve_memory, store_memory]
    agent = create_openai_functions_agent(llm, plan_tools, prompt)
    executor = AgentExecutor(agent=agent, tools=plan_tools, verbose=True)

    return executor


# ============= Global Instances =============

learning_agent_executor = create_learning_agent()
tutor_agent_executor = create_tutor_agent()
evaluator_agent_executor = create_evaluator_agent()
planner_agent_executor = create_planner_agent()

logger.info("LangChain agent executors initialized successfully")


# ============= Convenience Functions =============

async def run_learning_agent(user_input: str, user_id: int, session_id: str,
                            chat_history: List = None) -> Dict[str, Any]:
    """Run the general learning agent"""
    inputs = {
        "input": user_input,
        "chat_history": chat_history or []
    }

    try:
        result = await learning_agent_executor.ainvoke(inputs)
        return {"response": result.get("output", ""), "success": True}
    except Exception as e:
        logger.error(f"Error running learning agent: {e}")
        return {"response": "I encountered an error. Please try again.", "success": False, "error": str(e)}


async def run_tutor_agent(question: str, user_id: int, topic_id: int = None) -> Dict[str, Any]:
    """Run the tutor agent to explain something"""
    input_text = question
    if topic_id:
        input_text += f" (Search in topic_id: {topic_id})"

    try:
        result = await tutor_agent_executor.ainvoke({"input": input_text})
        return {"response": result.get("output", ""), "success": True}
    except Exception as e:
        logger.error(f"Error running tutor agent: {e}")
        return {"response": "I couldn't explain that topic right now.", "success": False, "error": str(e)}


async def run_quiz_agent(topic: str, difficulty: str = "medium",
                        num_questions: int = 5) -> Dict[str, Any]:
    """Generate a quiz for a topic"""
    input_text = f"Generate {num_questions} quiz questions about {topic} at {difficulty} difficulty"

    try:
        result = await evaluator_agent_executor.ainvoke({"input": input_text})
        return {"response": result.get("output", ""), "success": True}
    except Exception as e:
        logger.error(f"Error running quiz agent: {e}")
        return {"response": "I couldn't generate a quiz right now.", "success": False, "error": str(e)}


async def run_planner_agent(goal: str, user_id: int) -> Dict[str, Any]:
    """Create a learning roadmap"""
    weak_topics = await get_weak_topics(user_id)
    input_text = f"Create a learning roadmap for: {goal}"

    if weak_topics.get("weak_topics"):
        input_text += f"\n\nFocus on these weak areas: {', '.join(weak_topics['weak_topics'])}"

    try:
        result = await planner_agent_executor.ainvoke({"input": input_text})
        return {"response": result.get("output", ""), "success": True}
    except Exception as e:
        logger.error(f"Error running planner agent: {e}")
        return {"response": "I couldn't create a roadmap right now.", "success": False, "error": str(e)}


def create_summariser_agent() -> AgentExecutor:
    """Create a summariser agent for learning completion"""
    llm = get_groq_llm(temperature=0.3)

    system_prompt = """You are a learning summariser that creates comprehensive summaries.

You can use these tools:
- summarise_concepts: Generate a summary of key concepts after learning completion
- retrieve_memory: Check what topics were covered
- store_memory: Save the summary for future reference

Generate helpful summaries with key takeaways and next steps."""

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content="{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    summariser_tools = [summarise_concepts, retrieve_memory, store_memory]
    agent = create_openai_functions_agent(llm, summariser_tools, prompt)
    executor = AgentExecutor(agent=agent, tools=summariser_tools, verbose=True)

    return executor


summariser_agent_executor = create_summariser_agent()


async def run_summariser_agent(topics: List[str], quiz_results: List[Dict] = None) -> Dict[str, Any]:
    """Generate a summary after completing a learning session"""
    input_text = f"Summarize the learning session covering these topics: {', '.join(topics)}"

    if quiz_results:
        quiz_text = ", ".join([f"{r['topic']}: {r['score']}%" for r in quiz_results])
        input_text += f"\n\nQuiz results: {quiz_text}"

    try:
        result = await summariser_agent_executor.ainvoke({"input": input_text})
        return {"response": result.get("output", ""), "success": True}
    except Exception as e:
        logger.error(f"Error running summariser agent: {e}")
        return {"response": "I couldn't generate a summary right now.", "success": False, "error": str(e)}