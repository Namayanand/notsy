"""A2A Client - for delegating tasks to other agents"""
import json
import logging
from typing import Dict, Any, Optional, List
import httpx
from sse_starlette.sse import EventSourceResponse

from a2a.agent_card import AgentCard, AgentSkill
from a2a.task_manager import TaskStatus

logger = logging.getLogger(__name__)


class A2AClient:
    """Client for communicating with A2A agents"""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_agent_card(self, agent_url: str) -> Optional[AgentCard]:
        """Fetch agent card from an agent"""
        try:
            client = await self._get_client()
            response = await client.get(f"{agent_url}/.well-known/agent.json")
            response.raise_for_status()
            data = response.json()
            return AgentCard(**data)
        except Exception as e:
            logger.warning(f"Failed to get agent card from {agent_url}: {e}")
            return None

    async def send_task(
        self,
        agent_url: str,
        skill_id: str,
        message: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a task to an agent"""
        import uuid

        if task_id is None:
            task_id = str(uuid.uuid4())

        payload = {
            "taskId": task_id,
            "skill": {"id": skill_id},
            "message": {
                "role": "user",
                "content": message,
                "metadata": metadata or {}
            }
        }

        try:
            client = await self._get_client()
            response = await client.post(
                f"{agent_url}/tasks/send",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending task to {agent_url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending task to {agent_url}: {e}")
            raise

    async def get_task_status(
        self,
        agent_url: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Get task status from an agent"""
        try:
            client = await self._get_client()
            response = await client.get(f"{agent_url}/tasks/{task_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting task status from {agent_url}: {e}")
            raise

    async def cancel_task(
        self,
        agent_url: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Cancel a task"""
        try:
            client = await self._get_client()
            response = await client.post(
                f"{agent_url}/tasks/cancel",
                json={"taskId": task_id}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error cancelling task at {agent_url}: {e}")
            raise

    async def stream_task(
        self,
        agent_url: str,
        task_id: str
    ):
        """Stream task updates via SSE"""
        client = await self._get_client()

        async with client.stream(
            "GET",
            f"{agent_url}/tasks/{task_id}/stream"
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line[6:]

    async def wait_for_completion(
        self,
        agent_url: str,
        task_id: str,
        poll_interval: float = 1.0,
        max_wait: float = 120.0
    ) -> Dict[str, Any]:
        """Wait for task to complete (polling)"""
        import asyncio

        elapsed = 0.0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            task = await self.get_task_status(agent_url, task_id)
            status = task.get("status")

            if status == TaskStatus.COMPLETED.value:
                return task
            elif status == TaskStatus.FAILED.value:
                raise Exception(f"Task failed: {task.get('output', {}).get('content', 'Unknown error')}")

        raise TimeoutError(f"Task {task_id} did not complete within {max_wait}s")


class A2ADelegator:
    """Helper class for delegating to multiple agents"""

    def __init__(self):
        self.client = A2AClient()

    async def delegate_to_agent(
        self,
        agent_url: str,
        skill_id: str,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegate a task to a specific agent and wait for result"""
        task = await self.client.send_task(
            agent_url=agent_url,
            skill_id=skill_id,
            message=message,
            metadata=context
        )

        task_id = task.get("id")
        if not task_id:
            raise ValueError("Task ID not returned")

        # Wait for completion
        result = await self.client.wait_for_completion(agent_url, task_id)

        return {
            "task_id": task_id,
            "status": result.get("status"),
            "output": result.get("output"),
            "metadata": result.get("metadata", {})
        }

    async def close(self):
        """Close the client"""
        await self.client.close()