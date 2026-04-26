"""Orchestrator Agent - A2A Server with LangGraph Coordination"""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import uuid

from a2a.base_agent import A2ABaseAgent
from a2a.agent_card import (
    ORCHESTRATOR_SKILLS,
    AgentCapabilities
)
from a2a.client import A2AClient, A2ADelegator
from a2a.registry import AgentRegistry, DEFAULT_AGENTS
from orchestrator.graph import run_orchestrator, get_orchestrator_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Agent endpoints - configurable via environment
AGENT_ENDPOINTS = {
    "planner": os.getenv("AGENT_PLANNER_URL", os.getenv("PLANNER_URL", "http://localhost:8001")),
    "tutor": os.getenv("AGENT_TUTOR_URL", os.getenv("TUTOR_URL", "http://localhost:8002")),
    "evaluator": os.getenv("AGENT_EVALUATOR_URL", os.getenv("EVALUATOR_URL", "http://localhost:8003")),
    "motivator": os.getenv("AGENT_MOTIVATOR_URL", os.getenv("MOTIVATOR_URL", "http://localhost:8004")),
    "retriever": os.getenv("AGENT_RETRIEVER_URL", os.getenv("RETRIEVER_URL", "http://localhost:8005")),
    "memory": os.getenv("AGENT_MEMORY_URL", os.getenv("MEMORY_URL", "http://localhost:8006")),
}


class OrchestratorAgent(A2ABaseAgent):
    """Orchestrator Agent - coordinates other agents using LangGraph"""

    def __init__(self):
        port = os.getenv("PORT", "8000")
        url = f"http://localhost:{port}"

        super().__init__(
            name="NOTSY Orchestrator Agent",
            description="Master agent that routes user requests to appropriate specialized agents",
            version="1.0.0",
            url=url,
            skills=ORCHESTRATOR_SKILLS,
            capabilities=AgentCapabilities(
                streaming=True,
                stateTransitionHistory=True
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
        )

        self.client = A2AClient()
        self.delegator = A2ADelegator()
        self.registry = AgentRegistry(agent_endpoints=AGENT_ENDPOINTS)
        self._agent_chain: List[Dict[str, Any]] = []

    async def execute_skill(
        self,
        skill_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the orchestrator skill - route to appropriate agent using LangGraph"""
        content = input_data.get("content", "")
        session_id = context.get("session_id", "")
        user_id = context.get("user_id", 0)
        task_id = context.get("task_id", str(uuid.uuid4()))
        notebook_id = input_data.get("notebook_id")
        learning_mode = input_data.get("learning_mode", "MASTER_THIS")

        self._agent_chain = []

        try:
            # Run the LangGraph orchestrator
            result = await run_orchestrator(
                task_id=task_id,
                user_id=str(user_id),
                session_id=session_id,
                user_message=content,
                notebook_id=notebook_id,
                learning_mode=learning_mode
            )

            self._agent_chain = [
                {"agent": agent, "skill": "auto", "duration": 0}
                for agent in result.get("agents_used", [])
            ]

            return {
                "result": {"message": result.get("response", "")},
                "agent_chain": self._agent_chain,
                "route": {"agent": result.get("intent", "unknown"), "skill": "auto"},
                "intent": result.get("intent"),
                "confidence": result.get("confidence")
            }

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            raise

    async def close(self):
        """Close client connections"""
        await self.delegator.close()
        await self.client.close()
        orch_graph = get_orchestrator_graph()
        await orch_graph.close()


# Create orchestrator app
orchestrator = OrchestratorAgent()
app = orchestrator.create_app()


# Add registry endpoint
@app.get("/registry")
async def get_registry():
    """Get all discovered agents and their skills"""
    await orchestrator.registry.discover_agents()
    return orchestrator.registry.to_dict()


# Override the default task handler to include agent chain tracking
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

    # Create task in Redis
    task = await orchestrator.task_manager.create_task(
        task_id=task_id,
        input_message=content,
        session_id=session_id,
        user_id=user_id,
        metadata={"skill_id": skill_id}
    )

    # Update to working
    await orchestrator.task_manager.update_task_status(task_id, "working")

    try:
        # Execute the skill via orchestrator
        result = await orchestrator.execute_skill(
            skill_id=skill_id or "auto",
            input_data={"content": content},
            context={
                "session_id": session_id,
                "user_id": user_id,
                "task_id": task_id
            }
        )

        # Format output
        output_content = json.dumps(result)

        # Update task to completed
        final_task = await orchestrator.task_manager.update_task_status(
            task_id,
            "completed",
            output_message=output_content,
            output_metadata={
                "skill_id": skill_id,
                "agent": orchestrator.name,
                "agent_chain": result.get("agent_chain", [])
            }
        )

        logger.info(f"Orchestrator: Task {task_id} completed")

        return final_task.model_dump()

    except Exception as e:
        logger.error(f"Orchestrator: Task {task_id} failed: {e}")
        await orchestrator.task_manager.update_task_status(
            task_id,
            "failed",
            output_message=f"Error: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# Add aggregated health endpoint for orchestrator
@app.get("/health")
async def get_orchestrator_health():
    """Get aggregated health status of all agents"""
    # Get orchestrator's own health
    orch_health = await orchestrator.get_health_status()

    # Get health from all agents in parallel
    import asyncio
    import httpx

    agent_names = ["planner", "tutor", "evaluator", "motivator", "retriever", "memory"]
    agent_healths = {}

    async def fetch_agent_health(name: str) -> tuple:
        url = AGENT_ENDPOINTS.get(name)
        if not url:
            return name, None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    return name, response.json()
        except Exception:
            pass
        return name, None

    results = await asyncio.gather(*[fetch_agent_health(name) for name in agent_names])

    total_tasks = 0
    system_status = "healthy"

    for name, health in results:
        if health:
            agent_healths[name] = {
                "status": health.get("status"),
                "tasks_completed": health.get("tasks", {}).get("completed", 0)
            }
            total_tasks += health.get("tasks", {}).get("completed", 0)

            if health.get("status") == "unhealthy":
                system_status = "unhealthy"
            elif health.get("status") == "degraded" and system_status == "healthy":
                system_status = "degraded"
        else:
            agent_healths[name] = {"status": "unreachable", "tasks_completed": 0}
            if system_status != "unhealthy":
                system_status = "unhealthy"

    return {
        "orchestrator": orch_health,
        "agents": agent_healths,
        "system_status": system_status,
        "total_tasks_processed": total_tasks
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)