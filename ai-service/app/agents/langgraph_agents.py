"""
LangGraph-based Agent Framework for NOTSY
Uses LangChain for tools, prompts, and LLM integration
"""
import os
import json
import logging
from json import JSONDecodeError, JSONDecoder
from typing import TypedDict, List, Dict, Any, Optional, Annotated, Sequence
from enum import Enum
from operator import add


def _extract_first_json(text: str):
    """
    Extract the first valid JSON value from *text* using JSONDecoder.raw_decode.
    Avoids greedy regex pitfalls with nested brackets.
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

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from groq import Groq

from app.agents.prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT_TEMPLATE,
    MEMORY_SYSTEM_PROMPT_TEMPLATE,
    MEMORY_USER_PROMPT_TEMPLATE,
    SUMMARISER_SYSTEM_PROMPT_TEMPLATE,
    SUMMARISER_USER_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)


# ============= State Definitions =============

class AgentState(TypedDict):
    """Main state for LangGraph agent workflow"""
    messages: Annotated[Sequence[BaseMessage], add]
    user_id: int
    session_id: str
    payload: Dict[str, Any]
    context: Dict[str, Any]
    agent_outputs: Dict[str, Any]
    current_agent: Optional[str]
    next_agent: Optional[str]
    error: Optional[str]


class LearningState(TypedDict):
    """State for learning workflow"""
    messages: Annotated[Sequence[BaseMessage], add]
    user_id: int
    session_id: str
    goal: str
    learning_mode: Optional[str]  # eli5 | medium | deep — controls tutor depth
    roadmap: List[Dict[str, Any]]
    current_topic_index: int
    current_topic: Optional[str]
    retrieved_documents: List[Dict[str, Any]]
    explanation: Optional[str]
    quiz_questions: List[Dict[str, Any]]
    quiz_answers: List[Dict[str, Any]]
    assessment_results: List[Dict[str, Any]]
    weak_topics: List[str]
    patterns: List[str]
    motivation_message: Optional[str]
    streak_data: Dict[str, Any]


# ============= LLM Setup =============

def get_llm(temperature: float = 0.3, model: str = None):
    """Get configured LLM instance"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not set")

    client = Groq(api_key=groq_api_key)
    model = model or "llama-3.3-70b-versatile"

    from langchain_groq import ChatGroq
    return ChatGroq(client=client, model=model, temperature=temperature)


# ============= LangChain Tools =============

@tool
async def search_notes_tool(query: str, topic_id: int, n_results: int = 5) -> Dict[str, Any]:
    """Search notes using vector store for a specific topic"""
    from app.services.vector_store import vector_store
    try:
        results = vector_store.query(topic_id, query, n_results=n_results)
        return results
    except Exception as e:
        logger.error(f"Error searching notes: {e}")
        return {"documents": [], "metadatas": [], "distances": []}


@tool
async def semantic_search_tool(query: str, notebook_id: Optional[int] = None,
                                 user_id: Optional[int] = None, n_results: int = 10) -> Dict[str, Any]:
    """Perform semantic search across user's content"""
    from app.services.vector_store import vector_store
    try:
        if notebook_id:
            results = vector_store.semantic_search(query, n_results=n_results, notebook_id=notebook_id)
        else:
            results = vector_store.global_search(query, n_results=n_results)
        return results
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return {"documents": [], "metadatas": [], "distances": []}


@tool
async def store_memory_tool(user_id: int, memory_type: str, content: str,
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Store a memory entry in long-term memory"""
    from app.core.memory_store import memory_store
    try:
        result = await memory_store.write(user_id, memory_type, content, metadata or {})
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        return {"success": False, "error": str(e)}


@tool
async def retrieve_memory_tool(user_id: int, query: str,
                                memory_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Retrieve memories from long-term memory"""
    from app.core.memory_store import memory_store
    try:
        results = await memory_store.read(user_id, query, memory_types)
        return results
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}")
        return []


@tool
async def get_streak_data_tool(user_id: int, topic_id: Optional[int] = None) -> Dict[str, Any]:
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


@tool
async def get_weak_topics_tool(user_id: int) -> Dict[str, Any]:
    """Retrieve user's weak topics from memory"""
    from app.core.memory_store import memory_store
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


# Tool list for ToolNode
langchain_tools = [
    search_notes_tool,
    semantic_search_tool,
    store_memory_tool,
    retrieve_memory_tool,
    get_streak_data_tool,
    get_weak_topics_tool,
]


# ============= Helper: LLM-as-Agent Tool Execution =============

async def run_llm_with_tools(llm, system_prompt: str, user_prompt: str,
                             tools: list, max_iterations: int = 5) -> str:
    """
    Execute LLM in agent mode: invoke LLM -> check tool_calls -> execute tools -> append ToolMessage -> repeat.
    Returns the final LLM response content.
    """
    from langchain_core.messages import HumanMessage, ToolMessage

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    for iteration in range(max_iterations):
        # Invoke LLM
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        # Check if LLM called any tools
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})

                # Find the tool
                tool = next((t for t in tools if t.name == tool_name), None)
                if tool:
                    try:
                        # Execute the tool
                        result = await tool.ainvoke(tool_args)
                        # Append ToolMessage
                        messages.append(ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call["id"]
                        ))
                    except Exception as e:
                        logger.error(f"Tool {tool_name} error: {e}")
                        messages.append(ToolMessage(
                            content=f"Error: {str(e)}",
                            tool_call_id=tool_call["id"]
                        ))
                else:
                    logger.warning(f"Tool {tool_name} not found")
        else:
            # No tool calls, return the response
            return response.content

    logger.warning(f"Max iterations ({max_iterations}) reached")
    return messages[-1].content if messages else ""


# ============= Agent Nodes =============

async def planner_node(state: LearningState) -> LearningState:
    """LangGraph node for the Planner Agent"""
    from app.core.memory_store import memory_store

    goal = state.get("goal", "")
    user_id = state["user_id"]
    session_id = state["session_id"]

    if not goal:
        state["error"] = "No goal provided"
        return state

    logger.info(f"LangGraph Planner: Creating roadmap for goal: {goal}")

    # Use LLM-as-agent pattern to get weak topics and create roadmap
    llm = get_llm(temperature=0.3)

    system_prompt = PLANNER_SYSTEM_PROMPT
    user_prompt = PLANNER_USER_PROMPT_TEMPLATE.format(goal=goal)

    try:
        content = await run_llm_with_tools(
            llm=llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=[get_weak_topics_tool],
            max_iterations=3
        )

        # Parse JSON
        try:
            roadmap = json.loads(content)
        except json.JSONDecodeError:
            try:
                roadmap = _extract_first_json(content)
            except json.JSONDecodeError:
                roadmap = []
    except Exception as e:
        logger.error(f"Error generating roadmap: {e}")
        roadmap = []

    if not roadmap:
        roadmap = [
            {"id": "topic_1", "name": f"Introduction to {goal}", "difficulty": 1, "duration_hours": 1.0, "prerequisites": [], "status": "pending"},
            {"id": "topic_2", "name": f"Core concepts of {goal}", "difficulty": 2, "duration_hours": 2.0, "prerequisites": ["topic_1"], "status": "pending"},
            {"id": "topic_3", "name": f"Advanced {goal}", "difficulty": 3, "duration_hours": 3.0, "prerequisites": ["topic_2"], "status": "pending"},
        ]

    state["roadmap"] = roadmap
    state["current_topic_index"] = 0
    state["current_topic"] = roadmap[0]["name"] if roadmap else None

    # Store in session context
    try:
        await memory_store.set_session_context(session_id, "roadmap", roadmap, ttl=7200)
    except Exception as e:
        logger.warning(f"Could not store roadmap: {e}")

    # Add message
    state["messages"].append(AIMessage(content=f"I've created a learning roadmap for '{goal}' with {len(roadmap)} topics."))

    return state


async def retriever_node(state: LearningState) -> LearningState:
    """LangGraph node for the Retriever Agent"""
    from app.services.vector_store import vector_store

    query = state.get("current_topic", "")
    if not query:
        query = "explain this topic"

    topic_id = state["payload"].get("topic_id")
    user_id = state["user_id"]

    logger.info(f"LangGraph Retriever: Searching for: {query}")

    # Perform semantic search
    if topic_id:
        results = vector_store.query(topic_id, query, n_results=5)
    else:
        results = vector_store.global_search(query, n_results=10)

    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])
    distances = results.get("distances", [])

    # Build sources
    sources = []
    if documents and documents[0]:
        for i, doc in enumerate(documents):
            if not doc:
                continue
            metadata = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0
            score = max(0, 1.0 - distance)

            sources.append({
                "content": doc[:500] + "..." if len(doc) > 500 else doc,
                "filename": metadata.get("source", "Unknown"),
                "score": round(score, 3),
                "metadata": metadata
            })

    state["retrieved_documents"] = sources

    # Add message
    state["messages"].append(AIMessage(content=f"Found {len(sources)} relevant documents for '{state.get('current_topic')}'."))

    return state


async def tutor_node(state: LearningState) -> LearningState:
    """LangGraph node for the Tutor Agent"""
    from app.core.memory_store import memory_store

    topic = state.get("current_topic", "")
    user_id = state["user_id"]
    session_id = state["session_id"]

    if not topic:
        state["error"] = "No topic available"
        return state

    logger.info(f"LangGraph Tutor: Explaining topic: {topic}")

    # Get retrieved documents as context
    documents = state.get("retrieved_documents", [])
    context = "\n\n".join([doc["content"] for doc in documents[:3]])

    # Determine explanation depth — prefer explicit state value, then check weak topics
    depth = state.get("learning_mode") or "medium"
    weak_topics = state.get("weak_topics", [])
    if topic in weak_topics and depth == "medium":
        depth = "eli5"

    # Generate explanation using LLM
    llm = get_llm(temperature=0.3)

    depth_instruction = {
        "eli5": "Explain in simple terms, like teaching a 5-year-old. Use analogies.",
        "medium": "Explain at an intermediate level with clear examples.",
        "deep": "Explain in depth with technical details and edge cases."
    }.get(depth, "Explain at an intermediate level with clear examples.")

    prompt = ChatPromptTemplate.from_template("""Explain the concept of "{topic}". {depth_instruction}

Context from study materials:
{context}

Provide a clear, structured explanation with examples. Cite sources where applicable.""")

    chain = prompt | llm

    try:
        response = await chain.ainvoke({"topic": topic, "depth_instruction": depth_instruction, "context": context or "No specific context provided."})
        explanation = response.content
    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        explanation = f"I couldn't generate an explanation for '{topic}' at this time."

    state["explanation"] = explanation

    # Store explanation in session
    try:
        await memory_store.set_session_context(session_id, "current_explanation", explanation, ttl=3600)
    except Exception:
        pass

    # Add message
    state["messages"].append(AIMessage(content=explanation))

    return state


async def evaluator_node(state: LearningState) -> LearningState:
    """LangGraph node for the Evaluator Agent"""
    from app.core.memory_store import memory_store

    topic = state.get("current_topic", "")
    user_id = state["user_id"]
    session_id = state["session_id"]

    if not topic:
        state["error"] = "No topic for quiz"
        return state

    logger.info(f"LangGraph Evaluator: Generating quiz for {topic}")

    # Generate quiz using LLM
    llm = get_llm(temperature=0.3)

    prompt = ChatPromptTemplate.from_template("""Generate 5 quiz questions about "{topic}" at medium difficulty.

Format as a JSON array with this structure:
[{{
  "question": "question text",
  "type": "multiple_choice",
  "options": ["option1", "option2", "option3", "option4"],
  "correct_answer": "option1",
  "explanation": "why this is correct"
}}]

Return ONLY the JSON array, no additional text.""")

    chain = prompt | llm

    try:
        response = await chain.ainvoke({"topic": topic})
        content = response.content

        try:
            questions = json.loads(content)
        except json.JSONDecodeError:
            try:
                questions = _extract_first_json(content)
            except json.JSONDecodeError:
                questions = []
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        questions = []

    if not questions:
        questions = [
            {"question": f"What is a key concept in {topic}?", "type": "multiple_choice", "options": ["Option A", "Option B", "Option C", "Option D"], "correct_answer": "Option A", "explanation": "This is the correct answer."}
        ]

    state["quiz_questions"] = questions

    # Store quiz in session
    try:
        await memory_store.set_session_context(session_id, "current_quiz", questions, ttl=3600)
    except Exception:
        pass

    # Add message
    state["messages"].append(AIMessage(content=f"I've generated {len(questions)} quiz questions about '{topic}'. Ready when you are!"))

    return state


async def memory_node(state: LearningState) -> LearningState:
    """LangGraph node for the Memory Agent"""
    from app.core.memory_store import memory_store

    user_id = state["user_id"]
    session_id = state["session_id"]
    topic = state.get("current_topic")

    logger.info(f"LangGraph Memory: Tracking session for {topic}")

    # Use LLM-as-agent pattern to store session and analyze patterns
    llm = get_llm(temperature=0.3)

    system_prompt = MEMORY_SYSTEM_PROMPT_TEMPLATE.format(topic=topic, user_id=user_id)
    user_prompt = MEMORY_USER_PROMPT_TEMPLATE.format(user_id=user_id, topic=topic)

    patterns = []
    try:
        content = await run_llm_with_tools(
            llm=llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=[store_memory_tool, retrieve_memory_tool],
            max_iterations=5
        )

        # Parse patterns from LLM response
        try:
            patterns = _extract_first_json(content)
            if not isinstance(patterns, list):
                patterns = []
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Could not parse patterns from LLM response: {e}")

    except Exception as e:
        logger.warning(f"LLM agent error: {e}")

    state["patterns"] = patterns

    # Update roadmap progress
    try:
        roadmap = state.get("roadmap", [])
        current_index = state.get("current_topic_index", 0)

        if roadmap and current_index < len(roadmap):
            roadmap[current_index]["status"] = "completed"
            state["roadmap"] = roadmap
            state["current_topic_index"] = current_index + 1

            if current_index + 1 < len(roadmap):
                state["current_topic"] = roadmap[current_index + 1]["name"]

        await memory_store.set_session_context(session_id, "roadmap", roadmap, ttl=7200)
    except Exception as e:
        logger.warning(f"Could not update roadmap: {e}")

    # Add message
    roadmap_len = len(roadmap) if roadmap else 0
    state["messages"].append(AIMessage(content=f"Session tracked! You've completed {current_index + 1} of {roadmap_len} topics."))

    return state


async def summariser_node(state: LearningState) -> LearningState:
    """LangGraph node for the Summariser Agent"""
    from app.core.memory_store import memory_store

    user_id = state["user_id"]
    session_id = state["session_id"]
    roadmap = state.get("roadmap", [])

    logger.info(f"LangGraph Summariser: Generating summary for user {user_id}")

    # Get topics covered
    topics_covered = []
    if roadmap:
        for item in roadmap:
            if item.get("status") == "completed":
                topics_covered.append(item.get("name"))

    if not topics_covered:
        current_topic = state.get("current_topic")
        if current_topic:
            topics_covered = [current_topic]

    if not topics_covered:
        state["messages"].append(AIMessage(content="No topics to summarize."))
        return state

    # Use LLM-as-agent pattern to get quiz results, store completion, and generate summary
    llm = get_llm(temperature=0.3)

    topics_text = ", ".join(topics_covered)
    topics_list = ", ".join([f"'{t}'" for t in topics_covered])
    system_prompt = SUMMARISER_SYSTEM_PROMPT_TEMPLATE.format(
        topics_text=topics_text,
        user_id=user_id,
        topics_list=topics_list
    )
    user_prompt = SUMMARISER_USER_PROMPT_TEMPLATE.format(
        user_id=user_id,
        topics_text=topics_text
    )

    summary = ""
    try:
        summary = await run_llm_with_tools(
            llm=llm,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=[retrieve_memory_tool, store_memory_tool],
            max_iterations=5
        )
    except Exception as e:
        logger.warning(f"LLM agent error: {e}")
        summary = f"You have completed learning: {topics_text}. Keep reviewing to reinforce your knowledge!"

    state["motivation_message"] = summary

    # Store summary in session
    try:
        await memory_store.set_session_context(session_id, "session_summary", summary, ttl=7200)
    except Exception:
        pass

    # Add message
    state["messages"].append(AIMessage(content=summary))

    return state


# ============= Routing Functions =============

def should_retrieve(state: LearningState) -> str:
    """Route from planner to retriever"""
    return "retriever"


def should_explain(state: LearningState) -> str:
    """Route from retriever to tutor"""
    return "tutor"


def should_quiz(state: LearningState) -> str:
    """Route from tutor to evaluator"""
    return "evaluator"


def should_track(state: LearningState) -> str:
    """Route from evaluator to memory"""
    return "memory"


def should_motivate(state: LearningState) -> str:
    """Route from memory to summariser"""
    return "summariser"


def is_learning_complete(state: LearningState) -> str:
    """Check if learning is complete"""
    roadmap = state.get("roadmap", [])
    current_index = state.get("current_topic_index", 0)

    if current_index >= len(roadmap):
        return "summariser"  # Done, go to summariser
    return "retriever"  # Continue with next topic


# ============= Graph Construction =============

def create_learning_graph() -> StateGraph:
    """Create the main learning workflow graph"""
    graph = StateGraph(LearningState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("tutor", tutor_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("memory", memory_node)
    graph.add_node("summariser", summariser_node)

    # Define edges
    graph.add_edge("__start__", "planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "tutor")
    graph.add_edge("tutor", "evaluator")
    graph.add_edge("evaluator", "memory")
    graph.add_edge("memory", "summariser")
    graph.add_edge("summariser", END)

    return graph


def create_conditional_learning_graph() -> StateGraph:
    """Create learning graph with conditional branching for topic iteration"""
    graph = StateGraph(LearningState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("tutor", tutor_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("memory", memory_node)
    graph.add_node("summariser", summariser_node)

    # Define edges
    graph.add_edge("__start__", "planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "tutor")
    graph.add_edge("tutor", "evaluator")
    graph.add_edge("evaluator", "memory")
    graph.add_edge("memory", "retriever")  # Loop back to process next topic

    # Add conditional routing
    graph.add_conditional_edges(
        "memory",
        is_learning_complete,
        {
            "retriever": "retriever",
            "summariser": "summariser"
        }
    )

    graph.add_edge("summariser", END)

    return graph


# ============= Runnable Interface =============

class LangGraphAgent:
    """Wrapper class to run LangGraph as an agent"""

    def __init__(self, graph: StateGraph):
        self.graph = graph.compile()

    async def ainvoke(self, initial_state: LearningState) -> LearningState:
        """Run the graph"""
        return await self.graph.ainvoke(initial_state)

    async def ainvoke_stream(self, initial_state: LearningState):
        """Run the graph with streaming"""
        async for event in self.graph.ainvoke(initial_state):
            yield event


# ============= Global Instances =============

learning_graph = create_learning_graph().compile()
conditional_learning_graph = create_conditional_learning_graph().compile()

logger.info("LangGraph agents initialized successfully")