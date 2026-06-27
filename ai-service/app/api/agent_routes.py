import os
import logging
import uuid
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.base import AgentInput
from app.core.orchestrator import orchestrator, initialize_orchestrator, FlowType
from app.core.memory_store import memory_store

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Session store — Redis-backed with in-memory fallback
# ---------------------------------------------------------------------------

_redis_client = None
_SESSION_TTL = 86400  # 24 hours


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return None
    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        logger.info("Session store: connected to Redis")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}), falling back to in-memory sessions")
        _redis_client = None
    return _redis_client


# Fallback in-memory dict used when Redis is not available
_sessions_local: Dict[str, Dict[str, Any]] = {}


def _set_session(session_id: str, data: Dict[str, Any]) -> None:
    r = _get_redis()
    if r:
        r.setex(f"session:{session_id}", _SESSION_TTL, json.dumps(data))
    else:
        _sessions_local[session_id] = data


def _get_session(session_id: str) -> Optional[Dict[str, Any]]:
    r = _get_redis()
    if r:
        raw = r.get(f"session:{session_id}")
        return json.loads(raw) if raw else None
    return _sessions_local.get(session_id)


def _delete_session(session_id: str) -> None:
    r = _get_redis()
    if r:
        r.delete(f"session:{session_id}")
    else:
        _sessions_local.pop(session_id, None)


def _session_exists(session_id: str) -> bool:
    return _get_session(session_id) is not None


# ---------------------------------------------------------------------------

# Initialize orchestrator on startup
_orchestrator_initialized = False


def get_orchestrator():
    """Get or initialize the orchestrator"""
    global _orchestrator_initialized
    if not _orchestrator_initialized:
        initialize_orchestrator()
        _orchestrator_initialized = True
    return orchestrator


# Request/Response models
class StartSessionRequest(BaseModel):
    user_id: int
    goal: str = Field(..., min_length=1)
    topic_id: Optional[int] = None
    notebook_id: Optional[int] = None
    learning_mode: Optional[str] = "medium"  # eli5 | medium | deep


class AgentMessageRequest(BaseModel):
    session_id: str
    message: str
    agent: Optional[str] = None
    payload: Dict[str, Any] = {}


class EvaluateAnswerRequest(BaseModel):
    session_id: str
    question: str
    user_answer: str
    correct_answer: str
    topic: str


@router.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await memory_store.connect()
    get_orchestrator()
    logger.info("Agent routes initialized")


@router.post("/start-session")
async def start_session(request: StartSessionRequest):
    """Start a new agent learning session"""
    session_id = str(uuid.uuid4())

    # Initialize session context in memory store
    await memory_store.set_session_context(session_id, "goal", request.goal)
    await memory_store.set_session_context(session_id, "user_id", request.user_id)
    await memory_store.set_session_context(session_id, "active_agents", [])
    await memory_store.set_session_context(session_id, "current_topics", [])
    await memory_store.set_session_context(session_id, "weak_topics", [])

    if request.topic_id:
        await memory_store.set_session_context(session_id, "topic_id", request.topic_id)
    if request.notebook_id:
        await memory_store.set_session_context(session_id, "notebook_id", request.notebook_id)

    _set_session(session_id, {
        "user_id": request.user_id,
        "goal": request.goal,
        "started_at": str(uuid.uuid4()),  # timestamp
        "topic_id": request.topic_id,
        "notebook_id": request.notebook_id,
        "learning_mode": request.learning_mode or "medium",
    })

    logger.info(f"Started session {session_id} for user {request.user_id}")

    return {
        "session_id": session_id,
        "status": "started",
        "message": "Session started. Send a message to begin the learning flow."
    }


@router.post("/message")
async def send_message(request: AgentMessageRequest):
    """Send a message to the active session"""
    session = _get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    user_id = session["user_id"]

    # Get session context
    context = await memory_store.get_all_session_context(request.session_id)

    # Create agent input
    input_data = AgentInput(
        user_id=user_id,
        session_id=request.session_id,
        payload=request.payload or {"message": request.message},
        context=context
    )

    # Execute appropriate flow
    orch = get_orchestrator()

    if request.agent:
        # Execute specific agent
        results = await orch.execute(
            FlowType.SEQUENTIAL,
            request.agent,
            input_data,
            context
        )
    else:
        # Default learning flow
        results = await orch.execute(
            FlowType.FEEDBACK_LOOP,
            "planner",
            input_data,
            context
        )

    # Update session context with results and persist to memory store
    updates = {}
    for result in results:
        updates[f"{result.agent_type}_result"] = result.result
        updates["active_agent"] = result.agent_type

    await memory_store.update_session_context(request.session_id, updates)
    context.update(updates)

    return {
        "results": [r.model_dump() for r in results],
        "session_id": request.session_id
    }


@router.get("/state/{session_id}")
async def get_session_state(session_id: str):
    """Get current session state"""
    session = _get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    context = await memory_store.get_all_session_context(session_id)

    # Get roadmap if exists
    roadmap = context.get("roadmap", [])
    current_index = context.get("current_topic_index", 0)
    current_topic = None
    if roadmap and isinstance(roadmap, list) and current_index < len(roadmap):
        current_topic = roadmap[current_index].get("name")

    return {
        "session_id": session_id,
        "goal": session.get("goal"),
        "active_agent": context.get("active_agent"),
        "roadmap": roadmap,
        "current_topic": current_topic,
        "current_topic_index": current_index,
        "context": context
    }


@router.get("/roadmap/{session_id}")
async def get_roadmap(session_id: str):
    """Get the current learning roadmap"""
    if not _session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    roadmap = await memory_store.get_session_context(session_id, "roadmap")
    current_index = await memory_store.get_session_context(session_id, "current_topic_index") or 0

    return {
        "roadmap": roadmap or [],
        "current_topic_index": current_index
    }


@router.post("/quiz/generate")
async def generate_quiz(session_id: str, topic: str, difficulty: str = "medium",
                        num_questions: int = 5):
    """Generate a quiz for a topic"""
    session = _get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    user_id = session["user_id"]

    # Execute evaluator agent to generate quiz
    context = await memory_store.get_all_session_context(session_id)
    orch = get_orchestrator()

    input_data = AgentInput(
        user_id=user_id,
        session_id=session_id,
        payload={
            "mode": "generate",
            "topic": topic,
            "difficulty": difficulty,
            "num_questions": num_questions
        },
        context=context
    )

    results = await orch.execute(FlowType.SEQUENTIAL, "evaluator", input_data, context)

    return {
        "quiz": results[0].result if results else {},
        "session_id": session_id
    }


@router.post("/quiz/evaluate")
async def evaluate_answer(request: EvaluateAnswerRequest):
    """Evaluate a user's quiz answer"""
    session = _get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    user_id = session["user_id"]

    # Execute evaluator agent
    context = await memory_store.get_all_session_context(request.session_id)
    orch = get_orchestrator()

    input_data = AgentInput(
        user_id=user_id,
        session_id=request.session_id,
        payload={
            "mode": "evaluate",
            "question": request.question,
            "answer": request.user_answer,
            "correct_answer": request.correct_answer,
            "topic": request.topic
        },
        context=context
    )

    results = await orch.execute(FlowType.SEQUENTIAL, "evaluator", input_data, context)

    return {
        "feedback": results[0].result if results else {},
        "session_id": request.session_id
    }


@router.get("/insights/{user_id}")
async def get_insights(user_id: int):
    """Get learning insights for a user"""
    try:
        insights = await memory_store.get_insights(user_id)
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/stream/{session_id}")
async def stream_session(websocket: WebSocket, session_id: str):
    """WebSocket for real-time agent streaming"""
    session = _get_session(session_id)
    if session is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    try:
        user_id = session["user_id"]
        context = await memory_store.get_all_session_context(session_id)
        orch = get_orchestrator()

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Process and stream results
            input_data = AgentInput(
                user_id=user_id,
                session_id=session_id,
                payload=message,
                context=context
            )

            async for event in orch.execute_stream(
                FlowType.FEEDBACK_LOOP,
                "planner",
                input_data,
                context
            ):
                await websocket.send_json(event)

                # Update context from event
                if event["type"] == "agent_complete":
                    context[f"{event['data']['agent']}_result"] = event["data"]["result"]
                    context["active_agent"] = event["data"]["agent"]

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"type": "error", "data": {"error": str(e)}})


@router.post("/end-session/{session_id}")
async def end_session(session_id: str):
    """End an agent session"""
    _delete_session(session_id)

    # Clean up session context from memory store
    from app.core.memory_store import memory_store
    await memory_store.in_memory.delete_session(session_id)

    return {"status": "ended", "session_id": session_id}


# ============= LangGraph Routes =============

@router.post("/langgraph/start")
async def langgraph_start_session(request: StartSessionRequest):
    """Start a new LangGraph learning session"""
    session_id = str(uuid.uuid4())

    # Initialize session context
    await memory_store.set_session_context(session_id, "goal", request.goal)
    await memory_store.set_session_context(session_id, "user_id", request.user_id)
    await memory_store.set_session_context(session_id, "topic_id", request.topic_id)
    await memory_store.set_session_context(session_id, "notebook_id", request.notebook_id)

    _set_session(session_id, {
        "user_id": request.user_id,
        "goal": request.goal,
        "started_at": str(uuid.uuid4()),
        "topic_id": request.topic_id,
        "notebook_id": request.notebook_id,
        "learning_mode": request.learning_mode or "medium",
        "agent_type": "langgraph",
    })

    logger.info(f"Started LangGraph session {session_id} for user {request.user_id}")

    return {
        "session_id": session_id,
        "status": "started",
        "agent_type": "langgraph",
        "message": "LangGraph session started. Use /langgraph/run to execute the workflow."
    }


@router.post("/langgraph/run")
async def langgraph_run_workflow(session_id: str, goal: str = None):
    """Run the LangGraph learning workflow"""
    session = _get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    user_id = session["user_id"]

    # Get goal from session or parameter
    learning_goal = goal or session.get("goal", "General Learning")

    # Build initial state for LangGraph
    from app.agents.langgraph_agents import learning_graph
    from langchain_core.messages import HumanMessage

    initial_state = {
        "messages": [HumanMessage(content=f"I want to learn about {learning_goal}")],
        "user_id": user_id,
        "session_id": session_id,
        "goal": learning_goal,
        "learning_mode": session.get("learning_mode", "medium"),
        "roadmap": [],
        "current_topic_index": 0,
        "current_topic": None,
        "retrieved_documents": [],
        "explanation": None,
        "quiz_questions": [],
        "quiz_answers": [],
        "assessment_results": [],
        "weak_topics": [],
        "patterns": [],
        "motivation_message": None,
        "streak_data": {},
    }

    try:
        result = await learning_graph.ainvoke(initial_state)
        return {
            "result": result,
            "session_id": session_id,
            "agent_type": "langgraph"
        }
    except Exception as e:
        logger.error(f"LangGraph workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/langgraph/run-stream")
async def langgraph_run_stream(session_id: str, goal: str = None):
    """Run LangGraph workflow with streaming"""
    session = _get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    user_id = session["user_id"]

    learning_goal = goal or session.get("goal", "General Learning")

    from app.agents.langgraph_agents import learning_graph
    from langchain_core.messages import HumanMessage

    initial_state = {
        "messages": [HumanMessage(content=f"I want to learn about {learning_goal}")],
        "user_id": user_id,
        "session_id": session_id,
        "goal": learning_goal,
        "learning_mode": session.get("learning_mode", "medium"),
        "roadmap": [],
        "current_topic_index": 0,
        "current_topic": None,
        "retrieved_documents": [],
        "explanation": None,
        "quiz_questions": [],
        "quiz_answers": [],
        "assessment_results": [],
        "weak_topics": [],
        "patterns": [],
        "motivation_message": None,
        "streak_data": {},
    }

    async def generate():
        try:
            async for event in learning_graph.astream(initial_state):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"LangGraph stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============= LangChain Routes =============

@router.post("/langchain/chat")
async def langchain_chat(user_id: int, message: str):
    """Chat with the LangChain learning agent"""
    from app.agents.langchain_agents import run_learning_agent

    try:
        result = await run_learning_agent(message, user_id, str(uuid.uuid4()))
        return result
    except Exception as e:
        logger.error(f"LangChain chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/langchain/tutor")
async def langchain_tutor(user_id: int, question: str, topic_id: int = None):
    """Chat with the LangChain tutor agent"""
    from app.agents.langchain_agents import run_tutor_agent

    try:
        result = await run_tutor_agent(question, user_id, topic_id)
        return result
    except Exception as e:
        logger.error(f"LangChain tutor error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/langchain/quiz")
async def langchain_quiz(topic: str, difficulty: str = "medium", num_questions: int = 5):
    """Generate a quiz using the LangChain evaluator agent"""
    from app.agents.langchain_agents import run_quiz_agent

    try:
        result = await run_quiz_agent(topic, difficulty, num_questions)
        return result
    except Exception as e:
        logger.error(f"LangChain quiz error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/langchain/planner")
async def langchain_planner(user_id: int, goal: str):
    """Create a learning roadmap using the LangChain planner agent"""
    from app.agents.langchain_agents import run_planner_agent

    try:
        result = await run_planner_agent(goal, user_id)
        return result
    except Exception as e:
        logger.error(f"LangChain planner error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry")
async def get_agent_registry():
    """Get agent registry - returns LangChain and LangGraph as internal agents"""
    service_url = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
    agents = [
        {
            "name": "langchain",
            "url": service_url,
            "card": {
                "name": "langchain",
                "description": "LangChain-based learning agent with tool use capabilities",
                "version": "1.0.0",
                "url": service_url,
                "skills": [
                    {"id": "learning", "name": "General Learning", "description": "Helps with learning any topic"},
                    {"id": "tutoring", "name": "Tutoring", "description": "Explains concepts at various depth levels"},
                    {"id": "quiz", "name": "Quiz Generation", "description": "Creates quizzes and evaluates answers"},
                    {"id": "planning", "name": "Roadmap Planning", "description": "Creates learning roadmaps"}
                ]
            }
        },
        {
            "name": "langgraph",
            "url": service_url,
            "card": {
                "name": "langgraph",
                "description": "LangGraph-based workflow agent with stateful learning pipelines",
                "version": "1.0.0",
                "url": service_url,
                "skills": [
                    {"id": "learning_workflow", "name": "Learning Workflow", "description": "Full learning pipeline: plan -> retrieve -> tutor -> quiz -> track"},
                    {"id": "conditional_learning", "name": "Adaptive Learning", "description": "Adapts based on user performance"}
                ]
            }
        }
    ]

    skills = []
    for agent in agents:
        for skill in agent["card"]["skills"]:
            skills.append({
                "agent_name": agent["name"],
                "agent_url": agent["url"],
                **skill
            })

    return {"agents": agents, "skills": skills}