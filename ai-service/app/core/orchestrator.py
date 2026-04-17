import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from enum import Enum

from app.agents.base import BaseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class FlowType(Enum):
    """Orchestration flow types"""
    SEQUENTIAL = "sequential"          # A → B → C → ...
    CONDITIONAL = "conditional"       # A → B (if X) else C
    FEEDBACK_LOOP = "feedback_loop"  # A → B → C → A (repeat)


class Orchestrator:
    """Central controller for agent orchestration"""

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._flows: Dict[str, List[str]] = {
            "learning": ["planner", "retriever", "tutor", "evaluator", "memory", "motivator"],
            "quiz": ["evaluator", "memory"],
            "review": ["retriever", "tutor"],
        }

    def register_agent(self, name: str, agent: BaseAgent):
        """Register an agent with the orchestrator"""
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")

    def register_agents(self, agents: Dict[str, BaseAgent]):
        """Register multiple agents at once"""
        for name, agent in agents.items():
            self.register_agent(name, agent)

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name"""
        return self.agents.get(name)

    def set_flow(self, flow_name: str, agent_sequence: List[str]):
        """Define a custom flow"""
        self._flows[flow_name] = agent_sequence

    async def execute(
        self,
        flow: FlowType,
        start_agent: str,
        input: AgentInput,
        context: Dict[str, Any] = None
    ) -> List[AgentOutput]:
        """Execute an agent workflow"""
        results = []
        current_input = input
        current_context = context.copy() if context else {}
        visited = set()
        max_iterations = 10

        current_agent = start_agent

        while current_agent and len(visited) < max_iterations:
            if current_agent in visited:
                logger.warning(f"Preventing infinite loop: {current_agent} already visited")
                break
            visited.add(current_agent)

            agent = self.agents.get(current_agent)
            if not agent:
                logger.warning(f"Agent not found: {current_agent}")
                break

            # Inject shared context
            current_input.context = current_context

            logger.info(f"Executing agent: {current_agent}")

            # Execute agent
            try:
                output = await agent.run(current_input)
                results.append(output)

                # Update shared context
                current_context[f"{output.agent_type}_result"] = output.result
                current_context["active_agent"] = output.agent_type

                # Determine next agent based on flow type
                if flow == FlowType.SEQUENTIAL:
                    current_agent = output.next_agent
                elif flow == FlowType.CONDITIONAL:
                    current_agent = self._evaluate_condition(output, current_context)
                elif flow == FlowType.FEEDBACK_LOOP:
                    # Check if we should continue the loop
                    if self._should_continue(output, current_context):
                        current_agent = output.next_agent
                    else:
                        current_agent = None  # End the loop
            except Exception as e:
                logger.error(f"Error executing agent {current_agent}: {e}")
                results.append(AgentOutput(
                    agent_type=current_agent,
                    result={"error": str(e)},
                    next_agent=None,
                    metadata={"error": True}
                ))
                break

        return results

    async def execute_stream(
        self,
        flow: FlowType,
        start_agent: str,
        input: AgentInput,
        context: Dict[str, Any] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute an agent workflow with streaming updates"""
        current_input = input
        current_context = context.copy() if context else {}
        visited = set()
        max_iterations = 10

        current_agent = start_agent

        while current_agent and len(visited) < max_iterations:
            if current_agent in visited:
                break
            visited.add(current_agent)

            agent = self.agents.get(current_agent)
            if not agent:
                break

            current_input.context = current_context

            # Stream agent start
            yield {"type": "agent_start", "data": {"agent": current_agent}}

            # Execute agent
            try:
                output = await agent.run(current_input)

                # Stream agent completion
                yield {"type": "agent_complete", "data": {
                    "agent": current_agent,
                    "result": output.result,
                    "next_agent": output.next_agent
                }}

                # Update context
                current_context[f"{output.agent_type}_result"] = output.result
                current_context["active_agent"] = output.agent_type

                # Determine next agent
                if flow == FlowType.SEQUENTIAL:
                    current_agent = output.next_agent
                elif flow == FlowType.CONDITIONAL:
                    current_agent = self._evaluate_condition(output, current_context)
                elif flow == FlowType.FEEDBACK_LOOP:
                    if self._should_continue(output, current_context):
                        current_agent = output.next_agent
                    else:
                        current_agent = None

            except Exception as e:
                logger.error(f"Error in stream for {current_agent}: {e}")
                yield {"type": "agent_error", "data": {
                    "agent": current_agent,
                    "error": str(e)
                }}
                break

        yield {"type": "flow_complete", "data": {"total_agents": len(visited)}}

    def _evaluate_condition(self, output: AgentOutput, context: Dict[str, Any]) -> Optional[str]:
        """Evaluate conditional branching"""
        # Simple rule: if evaluator says wrong answer, go back to tutor
        if output.agent_type == "evaluator":
            metadata = output.metadata or {}
            if not metadata.get("is_correct", True):
                return "tutor"

        return output.next_agent

    def _should_continue(self, output: AgentOutput, context: Dict[str, Any]) -> bool:
        """Determine if feedback loop should continue"""
        # Continue if:
        # 1. Last agent was memory and there are patterns to address
        # 2. Last agent was evaluator and user needs more practice

        if output.agent_type == "memory":
            result = output.result or {}
            patterns = result.get("patterns", [])
            return len(patterns) > 0

        if output.agent_type == "evaluator":
            metadata = output.metadata or {}
            # Continue if user got it wrong
            return not metadata.get("is_correct", True)

        return False

    def get_flow_agents(self, flow_name: str) -> List[str]:
        """Get agents in a flow"""
        return self._flows.get(flow_name, [])


# Global orchestrator instance
orchestrator = Orchestrator()


def initialize_orchestrator():
    """Initialize and register all agents"""
    from app.agents import (
        PlannerAgent, TutorAgent, EvaluatorAgent,
        MemoryAgent, MotivatorAgent, RetrieverAgent
    )

    orchestrator.register_agents({
        "planner": PlannerAgent(),
        "tutor": TutorAgent(),
        "evaluator": EvaluatorAgent(),
        "memory": MemoryAgent(),
        "motivator": MotivatorAgent(),
        "retriever": RetrieverAgent(),
    })

    logger.info("Initialized orchestrator with all 6 agents")
    return orchestrator