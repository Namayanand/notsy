from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class AgentInput(BaseModel):
    """Input model for agent execution"""
    user_id: int
    session_id: str
    payload: Dict[str, Any]
    context: Dict[str, Any] = {}


class AgentOutput(BaseModel):
    """Output model from agent execution"""
    agent_type: str
    result: Dict[str, Any]
    next_agent: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseAgent(ABC):
    """Abstract base class for all agents"""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the agent with given input and return output"""
        pass

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool from the tool registry"""
        from app.core.tools import tools
        return await tools.execute(tool_name, **kwargs)

    def _format_response(self, result: Dict[str, Any], next_agent: Optional[str] = None) -> AgentOutput:
        """Helper to format agent output"""
        return AgentOutput(
            agent_type=self.name,
            result=result,
            next_agent=next_agent,
            metadata={}
        )