"""A2A Task Manager - handles task state management with Redis persistence"""
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status as defined in A2A protocol"""
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskMessage(BaseModel):
    """Message within a task - input or output"""
    role: str = Field(default="user", description="Message role: user or agent")
    content: str = Field(..., description="Message content")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class A2ATask(BaseModel):
    """A2A Task object as defined in the protocol"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique task ID")
    status: TaskStatus = Field(default=TaskStatus.SUBMITTED, description="Current task status")
    input: Optional[TaskMessage] = Field(default=None, description="Task input message")
    output: Optional[TaskMessage] = Field(default=None, description="Task output message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def update_status(self, new_status: TaskStatus) -> None:
        """Update task status with timestamp"""
        self.status = new_status
        self.updated_at = datetime.utcnow().isoformat()


class TaskManager:
    """Manages A2A task state with Redis persistence"""

    def __init__(self, redis_url: str = "redis://localhost:6379", task_ttl: int = 3600):
        self.redis_url = redis_url
        self.task_ttl = task_ttl
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection"""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    def _task_key(self, task_id: str) -> str:
        """Generate Redis key for task"""
        return f"a2a:task:{task_id}"

    async def create_task(
        self,
        task_id: Optional[str] = None,
        input_message: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> A2ATask:
        """Create a new task"""
        if task_id is None:
            task_id = str(uuid.uuid4())

        task = A2ATask(
            id=task_id,
            status=TaskStatus.SUBMITTED,
            input=TaskMessage(
                role="user",
                content=input_message or "",
                metadata={
                    "session_id": session_id,
                    "user_id": user_id,
                    **(metadata or {})
                }
            ) if input_message else None,
            metadata=metadata or {}
        )

        await self._save_task(task)
        return task

    async def _save_task(self, task: A2ATask) -> None:
        """Save task to Redis"""
        redis_client = await self._get_redis()
        key = self._task_key(task.id)
        data = task.model_dump_json()
        await redis_client.setex(key, self.task_ttl, data)
        logger.info(f"Task {task.id} saved to Redis")

    async def get_task(self, task_id: str) -> Optional[A2ATask]:
        """Get task by ID"""
        redis_client = await self._get_redis()
        key = self._task_key(task_id)
        data = await redis_client.get(key)
        if data:
            return A2ATask.model_validate_json(data)
        return None

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        output_message: Optional[str] = None,
        output_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[A2ATask]:
        """Update task status and optionally add output"""
        task = await self.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return None

        task.update_status(status)

        if output_message:
            task.output = TaskMessage(
                role="agent",
                content=output_message,
                metadata=output_metadata or {}
            )

        await self._save_task(task)
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        redis_client = await self._get_redis()
        key = self._task_key(task_id)
        result = await redis_client.delete(key)
        return result > 0

    async def list_tasks(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[A2ATask]:
        """List tasks - NOTE: This is a simplified implementation.
        In production, you'd want to maintain indices for efficient querying."""
        redis_client = await self._get_redis()
        keys = await redis_client.keys("a2a:task:*")

        tasks = []
        for key in keys[:limit]:
            data = await redis_client.get(key)
            if data:
                task = A2ATask.model_validate_json(data)

                # Filter by session_id or user_id if provided
                if session_id and task.input and task.input.metadata.get("session_id") != session_id:
                    continue
                if user_id and task.input and task.input.metadata.get("user_id") != user_id:
                    continue

                tasks.append(task)

        return sorted(tasks, key=lambda t: t.created_at, reverse=True)