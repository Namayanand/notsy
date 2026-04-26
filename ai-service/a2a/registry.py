"""Agent Registry - discovers and tracks available A2A agents"""
import logging
from typing import Dict, Any, Optional, List
import httpx
import asyncio

from a2a.agent_card import AgentCard

logger = logging.getLogger(__name__)


# Default agent endpoints (LangChain + LangGraph are internal to orchestrator)
DEFAULT_AGENTS = {
    "orchestrator": "http://localhost:8000",
}


class AgentRegistry:
    """Registry for discovering and caching agent cards"""

    def __init__(
        self,
        agent_endpoints: Dict[str, str] = None,
        refresh_interval: int = 60
    ):
        self.agent_endpoints = agent_endpoints or DEFAULT_AGENTS
        self.refresh_interval = refresh_interval
        self._agent_cards: Dict[str, AgentCard] = {}
        self._refresh_task: Optional[asyncio.Task] = None

    async def discover_agents(self) -> Dict[str, AgentCard]:
        """Discover all agents by fetching their agent cards"""
        discovered = {}
        client = httpx.AsyncClient(timeout=10.0)

        async def fetch_agent_card(name: str, url: str) -> tuple:
            try:
                response = await client.get(f"{url}/.well-known/agent.json")
                response.raise_for_status()
                data = response.json()
                card = AgentCard(**data)
                logger.info(f"Discovered agent: {name} at {url}")
                return name, card
            except Exception as e:
                logger.warning(f"Failed to discover agent {name} at {url}: {e}")
                return name, None

        # Fetch all agent cards concurrently
        results = await asyncio.gather(
            *[fetch_agent_card(name, url) for name, url in self.agent_endpoints.items()],
            return_exceptions=True
        )

        await client.aclose()

        for result in results:
            if isinstance(result, Exception):
                continue
            name, card = result
            if card:
                discovered[name] = card
                self._agent_cards[name] = card

        return discovered

    async def get_agent_card(self, agent_name: str) -> Optional[AgentCard]:
        """Get agent card by name"""
        # Try to get from cache first
        if agent_name in self._agent_cards:
            return self._agent_cards[agent_name]

        # Try to fetch directly
        url = self.agent_endpoints.get(agent_name)
        if url:
            client = httpx.AsyncClient(timeout=10.0)
            try:
                response = await client.get(f"{url}/.well-known/agent.json")
                response.raise_for_status()
                card = AgentCard(**response.json())
                self._agent_cards[agent_name] = card
                return card
            except Exception as e:
                logger.warning(f"Failed to get agent card for {agent_name}: {e}")
                return None
            finally:
                await client.aclose()

        return None

    def get_agent_url(self, agent_name: str) -> Optional[str]:
        """Get agent URL by name"""
        return self.agent_endpoints.get(agent_name)

    def get_all_agents(self) -> Dict[str, AgentCard]:
        """Get all cached agent cards"""
        return self._agent_cards.copy()

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Get all skills from all discovered agents"""
        skills = []
        for name, card in self._agent_cards.items():
            for skill in card.skills:
                skills.append({
                    "agent_name": name,
                    "agent_url": self.agent_endpoints.get(name),
                    **skill.model_dump()
                })
        return skills

    async def start_auto_refresh(self):
        """Start automatic agent card refresh"""
        async def refresh_loop():
            while True:
                await asyncio.sleep(self.refresh_interval)
                try:
                    await self.discover_agents()
                except Exception as e:
                    logger.warning(f"Agent refresh failed: {e}")

        self._refresh_task = asyncio.create_task(refresh_loop())

    async def stop_auto_refresh(self):
        """Stop automatic refresh"""
        if self._refresh_task:
            self._refresh_task.cancel()
            self._refresh_task = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary for API response"""
        agents = []
        for name, card in self._agent_cards.items():
            agents.append({
                "name": name,
                "url": self.agent_endpoints.get(name),
                "card": card.model_dump()
            })
        return {
            "agents": agents,
            "skills": self.get_all_skills()
        }