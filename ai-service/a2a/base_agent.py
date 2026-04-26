"""A2A Base Agent - abstract class for all A2A-compliant agents"""
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from a2a.agent_card import AgentCard, AgentSkill, AgentCapabilities
from a2a.task_manager import TaskManager, A2ATask, TaskStatus, TaskMessage

logger = logging.getLogger(__name__)


class AgentMetrics:
    """Track agent performance metrics"""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_latency_ms = 0
        self.last_task_at: Optional[datetime] = None

    def record_success(self, latency_ms: float):
        self.tasks_completed += 1
        self.total_latency_ms += latency_ms
        self.last_task_at = datetime.now(timezone.utc)

    def record_failure(self, latency_ms: float):
        self.tasks_failed += 1
        self.total_latency_ms += latency_ms
        self.last_task_at = datetime.now(timezone.utc)

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 100.0
        return (self.tasks_completed / total) * 100

    @property
    def avg_latency_ms(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.total_latency_ms / total

    def get_uptime_seconds(self) -> int:
        return int((datetime.now(timezone.utc) - self.start_time).total_seconds())


class A2ABaseAgent(ABC):
    """Abstract base class for A2A-compliant agents"""

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        url: str = "",
        skills: List[AgentSkill] = None,
        capabilities: AgentCapabilities = None,
        redis_url: str = "redis://localhost:6379"
    ):
        self.name = name
        self.description = description
        self.version = version
        self.url = url
        self.skills = skills or []
        self.capabilities = capabilities or AgentCapabilities()
        self.redis_url = redis_url
        self.task_manager = TaskManager(redis_url=redis_url)
        self.metrics = AgentMetrics()
        self.port = int(os.getenv("PORT", "8000"))
        self._app: Optional[FastAPI] = None
        self._redis_client = None

    @abstractmethod
    async def execute_skill(
        self,
        skill_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a skill with input data and context.
        Must be implemented by each agent."""
        pass

    def get_agent_card(self) -> AgentCard:
        """Get the agent card for discovery"""
        return AgentCard(
            name=self.name,
            description=self.description,
            version=self.version,
            url=self.url,
            capabilities=self.capabilities,
            skills=self.skills
        )

    async def _check_redis_health(self) -> str:
        """Check Redis connectivity"""
        try:
            import redis.asyncio as redis
            client = redis.from_url(self.redis_url)
            await client.ping()
            await client.aclose()
            return "connected"
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return "disconnected"

    async def _check_chroma_health(self) -> str:
        """Check ChromaDB connectivity"""
        try:
            chroma_url = os.getenv("CHROMA_URL", "http://localhost:8000")
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{chroma_url}/api/v1/heartbeat", timeout=5.0)
                if response.status_code == 200:
                    return "connected"
            return "disconnected"
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
            return "disconnected"

    async def _check_groq_health(self) -> str:
        """Check Groq API connectivity"""
        try:
            import httpx
            groq_key = os.getenv("GROQ_API_KEY", "")
            if not groq_key:
                return "unconfigured"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    return "reachable"
            return "unreachable"
        except Exception as e:
            logger.warning(f"Groq health check failed: {e}")
            return "unreachable"

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        # Check dependencies
        redis_status = await self._check_redis_health()
        chroma_status = await self._check_chroma_health()
        groq_status = await self._check_groq_health()

        # Determine overall status
        if redis_status == "disconnected":
            status = "unhealthy"
        elif groq_status == "unreachable" or (self.tasks_completed + self.tasks_failed) > 0 and self.metrics.success_rate < 70:
            status = "unhealthy"
        elif groq_status == "unreachable" or self.metrics.success_rate < 90:
            status = "degraded"
        else:
            status = "healthy"

        uptime_seconds = self.metrics.get_uptime_seconds()
        uptime_human = self._format_uptime(uptime_seconds)

        return {
            "agent_name": self.name,
            "version": self.version,
            "status": status,
            "uptime_seconds": uptime_seconds,
            "uptime_human": uptime_human,
            "port": self.port,
            "tasks": {
                "completed": self.metrics.tasks_completed,
                "failed": self.metrics.tasks_failed,
                "success_rate": f"{self.metrics.success_rate:.1f}%",
                "avg_latency_ms": int(self.metrics.avg_latency_ms)
            },
            "dependencies": {
                "redis": redis_status,
                "chromadb": chroma_status,
                "groq_api": groq_status
            },
            "skills": [skill.id for skill in self.skills],
            "last_task_at": self.metrics.last_task_at.isoformat() if self.metrics.last_task_at else None
        }

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime as human-readable string"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"

    def create_app(self) -> FastAPI:
        """Create FastAPI app with A2A endpoints"""
        app = FastAPI(
            title=f"NOTSY {self.name} Agent",
            description=self.description,
            version=self.version
        )

        # Agent Card endpoint
        @app.get("/.well-known/agent.json")
        async def get_agent_card():
            return self.get_agent_card().model_dump()

        # Task send endpoint
        @app.post("/tasks/send")
        async def send_task(request: Dict[str, Any]) -> Dict[str, Any]:
            return await self._handle_send_task(request)

        # Task get endpoint
        @app.get("/tasks/{task_id}")
        async def get_task(task_id: str) -> Dict[str, Any]:
            task = await self.task_manager.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return task.model_dump()

        # Task cancel endpoint
        @app.post("/tasks/cancel")
        async def cancel_task(request: Dict[str, Any]) -> Dict[str, Any]:
            task_id = request.get("taskId")
            if not task_id:
                raise HTTPException(status_code=400, detail="taskId is required")

            task = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                output_message="Task cancelled by user"
            )
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            return {"taskId": task_id, "status": task.status.value}

        # Task stream endpoint (SSE)
        @app.get("/tasks/{task_id}/stream")
        async def stream_task(task_id: str):
            async def event_generator():
                task = await self.task_manager.get_task(task_id)
                if not task:
                    yield {"event": "error", "data": json.dumps({"message": "Task not found"})}
                    return

                yield {"event": "status", "data": task.model_dump_json()}

                import asyncio
                for _ in range(30):
                    await asyncio.sleep(1)
                    task = await self.task_manager.get_task(task_id)
                    if task and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        yield {"event": "done", "data": task.model_dump_json()}
                        break
                    elif task:
                        yield {"event": "status", "data": task.model_dump_json()}

            return EventSourceResponse(event_generator())

        # Enhanced health endpoint
        @app.get("/health")
        async def health():
            return await self.get_health_status()

        self._app = app
        return app

    async def _handle_send_task(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming task - the main A2A entry point"""
        start_time = time.time()

        # Extract task details
        task_id = request.get("taskId", str(uuid.uuid4()))
        skill_id = request.get("skill", {}).get("id") if isinstance(request.get("skill"), dict) else request.get("skill")
        message = request.get("message", {})
        session_id = message.get("metadata", {}).get("session_id") if isinstance(message, dict) else None
        user_id = message.get("metadata", {}).get("user_id") if isinstance(message, dict) else None
        content = message.get("content", "") if isinstance(message, dict) else ""

        logger.info(f"Task {task_id}: Received task with skill={skill_id}")

        # Create task in Redis
        task = await self.task_manager.create_task(
            task_id=task_id,
            input_message=content,
            session_id=session_id,
            user_id=user_id,
            metadata={"skill_id": skill_id}
        )

        # Update to working
        await self.task_manager.update_task_status(task_id, TaskStatus.WORKING)

        try:
            # Execute the skill
            input_data = {"content": content}
            if isinstance(message, dict) and "metadata" in message:
                input_data.update(message.get("metadata", {}))

            result = await self.execute_skill(
                skill_id=skill_id,
                input_data=input_data,
                context={
                    "session_id": session_id,
                    "user_id": user_id,
                    "task_id": task_id
                }
            )

            # Format output
            output_content = json.dumps(result) if isinstance(result, dict) else str(result)

            # Update task to completed
            final_task = await self.task_manager.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                output_message=output_content,
                output_metadata={"skill_id": skill_id, "agent": self.name}
            )

            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_success(latency_ms)

            logger.info(f"Task {task_id}: Completed successfully in {latency_ms:.0f}ms")

            return final_task.model_dump()

        except Exception as e:
            # Record failure
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_failure(latency_ms)

            logger.error(f"Task {task_id}: Failed with error: {e}")
            await self.task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                output_message=f"Error: {str(e)}"
            )
            raise HTTPException(status_code=500, detail=str(e))