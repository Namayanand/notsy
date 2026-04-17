import os
import logging
import uuid
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.agents.base import AgentInput
from app.core.orchestrator import orchestrator, initialize_orchestrator, FlowType
from app.core.memory_store import memory_store

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active sessions in memory (would use Redis in production)
sessions: Dict[str, Dict[str, Any]] = {}

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
    goal: str
    topic_id: Optional[int] = None
    notebook_id: Optional[int] = None


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

    sessions[session_id] = {
        "user_id": request.user_id,
        "goal": request.goal,
        "started_at": str(uuid.uuid4()),  # timestamp
        "topic_id": request.topic_id,
        "notebook_id": request.notebook_id
    }

    logger.info(f"Started session {session_id} for user {request.user_id}")

    return {
        "session_id": session_id,
        "status": "started",
        "message": "Session started. Send a message to begin the learning flow."
    }


@router.post("/message")
async def send_message(request: AgentMessageRequest):
    """Send a message to the active session"""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[request.session_id]
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

    # Update session context with results
    for result in results:
        context[f"{result.agent_type}_result"] = result.result
        context["active_agent"] = result.agent_type

    return {
        "results": [r.model_dump() for r in results],
        "session_id": request.session_id
    }


@router.get("/state/{session_id}")
async def get_session_state(session_id: str):
    """Get current session state"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    context = await memory_store.get_all_session_context(session_id)
    session = sessions[session_id]

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
    if session_id not in sessions:
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
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
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
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[request.session_id]
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
    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    try:
        session = sessions[session_id]
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
    if session_id in sessions:
        del sessions[session_id]

    # Clean up session context
    from app.core.memory_store import memory_store
    await memory_store.in_memory.delete_session(session_id)

    return {"status": "ended", "session_id": session_id}