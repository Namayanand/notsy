"""Orchestrator Agent - LangGraph-based routing without A2A"""
import json
import logging
import os
from typing import Dict, Any
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
import uuid

from orchestrator.graph import run_orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="NOTSY Orchestrator",
    description="Master agent that routes user requests to LangGraph agents",
    version="1.0.0"
)

# In-memory task storage (simple version)
tasks: Dict[str, Dict[str, Any]] = {}


@app.post("/tasks/send")
async def send_task(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming task with orchestrator logic"""
    task_id = request.get("taskId", str(uuid.uuid4()))
    skill_id = request.get("skill", {}).get("id") if isinstance(request.get("skill"), dict) else request.get("skill")
    message = request.get("message", {})
    session_id = message.get("metadata", {}).get("session_id") if isinstance(message, dict) else None
    user_id = message.get("metadata", {}).get("user_id") if isinstance(message, dict) else None
    content = message.get("content", "") if isinstance(message, dict) else ""

    logger.info(f"Orchestrator: Task {task_id} received with skill={skill_id}")

    # Create task
    tasks[task_id] = {
        "id": task_id,
        "status": "working",
        "input": {"content": content, "session_id": session_id, "user_id": user_id},
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        # Execute the skill via orchestrator
        result = await run_orchestrator(
            task_id=task_id,
            user_id=str(user_id) if user_id else "0",
            session_id=session_id or "",
            user_message=content,
            notebook_id=request.get("message", {}).get("metadata", {}).get("notebook_id"),
            learning_mode=request.get("message", {}).get("metadata", {}).get("learning_mode", "MASTER_THIS")
        )

        # Format output
        output_data = {
            "result": {"message": result.get("response", "")},
            "agent_chain": [
                {"agent": agent, "skill": "auto", "duration": 0}
                for agent in result.get("agents_used", [])
            ],
            "route": {"agent": result.get("intent", "unknown"), "skill": "auto"},
            "intent": result.get("intent"),
            "confidence": result.get("confidence")
        }

        tasks[task_id].update({
            "status": "completed",
            "output": output_data,
            "completed_at": datetime.now(timezone.utc).isoformat()
        })

        logger.info(f"Orchestrator: Task {task_id} completed")

        return {
            "id": task_id,
            "status": "completed",
            "output": {"role": "agent", "content": json.dumps(output_data)},
            "created_at": tasks[task_id]["created_at"],
            "updated_at": tasks[task_id]["completed_at"]
        }

    except Exception as e:
        logger.error(f"Orchestrator: Task {task_id} failed: {e}")
        tasks[task_id].update({
            "status": "failed",
            "output": {"role": "agent", "content": f"Error: {str(e)}"},
            "failed_at": datetime.now(timezone.utc).isoformat()
        })
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task(task_id: str) -> Dict[str, Any]:
    """Get task by ID"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/health")
async def get_health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "orchestrator",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    return {
        "service": "NOTSY Orchestrator",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)