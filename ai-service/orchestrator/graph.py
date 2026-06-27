"""LangGraph-based orchestrator with intelligent routing - no A2A"""
import json
import logging
import os
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.constants import START

logger = logging.getLogger(__name__)

# Import internal agents directly (no HTTP calls)
from app.agents.langchain_agents import (
    semantic_search,
    retrieve_memory,
    store_memory,
    explain_concept,
    generate_roadmap,
    generate_quiz,
    generate_motivation,
    get_streak_data,
)
from app.agents.langgraph_agents import (
    learning_graph,
    conditional_learning_graph,
)


class Intent(str, Enum):
    EXPLAIN = "EXPLAIN"
    STUDY_PLAN = "STUDY_PLAN"
    QUIZ_ME = "QUIZ_ME"
    GRADE = "GRADE"
    MOTIVATE = "MOTIVATE"
    SEARCH = "SEARCH"
    MULTI = "MULTI"


class OrchestratorState(TypedDict):
    """State for the LangGraph orchestrator"""
    task_id: str
    user_id: str
    session_id: str
    user_message: str
    notebook_id: Optional[str]
    learning_mode: str
    intent: Optional[str]
    confidence: Optional[float]
    retrieved_chunks: Optional[list]
    memory_context: Optional[dict]
    agent_outputs: dict
    final_response: Optional[str]
    agents_used: list
    error: Optional[str]


class OrchestratorGraph:
    """LangGraph-based orchestrator with intelligent routing"""

    def __init__(self):
        self._graph = None
        self._compiled = None
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    async def close(self):
        pass

    async def classify_intent(self, state: OrchestratorState) -> OrchestratorState:
        """Classify user intent using Groq LLM"""
        user_message = state["user_message"]

        system_prompt = """You are an intent classifier for a student learning platform.
Classify the user message into ONE of these intents:
- EXPLAIN        → user wants a concept explained
- STUDY_PLAN     → user wants a study schedule or plan
- QUIZ_ME        → user wants to be tested or quizzed
- GRADE          → user wants feedback on their answer
- MOTIVATE       → user wants encouragement or is feeling stuck
- SEARCH         → user wants to find something in their notes
- MULTI          → request needs multiple agents (complex query)

Respond ONLY with valid JSON:
{
  "intent": "EXPLAIN",
  "confidence": 0.95,
  "reasoning": "User asked to explain a concept",
  "suggested_agents": ["retriever", "tutor"]
}"""

        try:
            import httpx
            client = httpx.AsyncClient(timeout=120.0)
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.groq_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
            )
            await client.aclose()

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                parsed = json.loads(content.strip("```json").strip("```").strip())

                intent = parsed.get("intent", "MULTI")
                confidence = parsed.get("confidence", 0.5)

                if confidence < 0.6:
                    intent = "MULTI"

                state["intent"] = intent
                state["confidence"] = confidence
                logger.info(f"Intent classified: {intent} (confidence: {confidence})")
            else:
                state["intent"] = "MULTI"
                state["confidence"] = 0.5

        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            state["intent"] = "MULTI"
            state["confidence"] = 0.5

        return state

    async def load_memory(self, state: OrchestratorState) -> OrchestratorState:
        """Load context from Memory - direct function call"""
        user_id = state["user_id"]
        session_id = state["session_id"]

        try:
            result = await retrieve_memory(
                user_id=int(user_id) if user_id.isdigit() else 1,
                query=state["user_message"],
                session_id=session_id
            )
            state["memory_context"] = result
            logger.info(f"Memory context loaded for user {user_id}")
        except Exception as e:
            logger.error(f"Memory load error: {e}")
            state["memory_context"] = {}

        state["agents_used"].append("memory")
        return state

    async def retrieve_chunks(self, state: OrchestratorState) -> OrchestratorState:
        """Retrieve relevant chunks - direct function call"""
        query = state["user_message"]
        notebook_id = state.get("notebook_id")

        try:
            result = await semantic_search(
                query=query,
                notebook_id=int(notebook_id) if notebook_id and notebook_id.isdigit() else None,
                n_results=5
            )
            state["retrieved_chunks"] = result.get("results", [])
            logger.info(f"Retrieved {len(state.get('retrieved_chunks', []))} chunks")
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            state["retrieved_chunks"] = []

        return state

    async def run_tutor(self, state: OrchestratorState) -> OrchestratorState:
        """Run Tutor agent - direct function call"""
        try:
            result = await explain_concept(
                topic=state["user_message"],
                depth=state.get("learning_mode", "MASTER_THIS").lower(),
                context=state.get("retrieved_chunks", [])
            )
            state["agent_outputs"]["tutor"] = result.get("explanation", "Could not generate explanation")
            state["agents_used"].append("tutor")
        except Exception as e:
            logger.error(f"Tutor error: {e}")
            state["agent_outputs"]["tutor"] = f"Error: {str(e)}"

        return state

    async def run_planner(self, state: OrchestratorState) -> OrchestratorState:
        """Run Planner agent - direct function call"""
        try:
            memory_context = state.get("memory_context", {})
            result = await generate_roadmap(
                goal=state["user_message"],
                weak_topics=memory_context.get("weak_topics", [])
            )
            state["agent_outputs"]["planner"] = result.get("roadmap", "Could not generate roadmap")
            state["agents_used"].append("planner")
        except Exception as e:
            logger.error(f"Planner error: {e}")
            state["agent_outputs"]["planner"] = f"Error: {str(e)}"

        return state

    async def run_evaluator_quiz(self, state: OrchestratorState) -> OrchestratorState:
        """Run Evaluator agent for quiz - direct function call"""
        try:
            result = await generate_quiz(
                topic=state["user_message"],
                difficulty="medium",
                num_questions=5
            )
            state["agent_outputs"]["evaluator"] = result.get("quiz", "Could not generate quiz")
            state["agents_used"].append("evaluator")
        except Exception as e:
            logger.error(f"Evaluator error: {e}")
            state["agent_outputs"]["evaluator"] = f"Error: {str(e)}"

        return state

    async def run_motivator(self, state: OrchestratorState) -> OrchestratorState:
        """Run Motivator agent - direct function call"""
        try:
            user_id = int(state["user_id"]) if state["user_id"].isdigit() else 1
            streak_data = await get_streak_data(user_id=user_id)
            result = await generate_motivation(streak_data=streak_data)
            state["agent_outputs"]["motivator"] = result.get("message", "")
            state["agents_used"].append("motivator")
        except Exception as e:
            logger.error(f"Motivator error: {e}")
            state["agent_outputs"]["motivator"] = ""

        return state

    async def run_parallel_agents(self, state: OrchestratorState) -> OrchestratorState:
        """Run multiple agents in parallel for MULTI intent"""
        import asyncio

        # Create copies for parallel execution
        states = []
        for name in ["tutor", "planner", "evaluator"]:
            s = state.copy()
            s["agent_outputs"] = {}
            states.append(s)

        async def run_tutor_task(s):
            return await self.run_tutor(s)

        async def run_planner_task(s):
            return await self.run_planner(s)

        async def run_evaluator_task(s):
            return await self.run_evaluator_quiz(s)

        results = await asyncio.gather(
            run_tutor_task(states[0]),
            run_planner_task(states[1]),
            run_evaluator_task(states[2]),
            return_exceptions=True
        )

        # Merge results
        for r in results:
            if isinstance(r, OrchestratorState):
                state["agent_outputs"].update(r.get("agent_outputs", {}))
                for agent in r.get("agents_used", []):
                    if agent not in state["agents_used"]:
                        state["agents_used"].append(agent)

        return state

    async def format_retrieval_response(self, state: OrchestratorState) -> OrchestratorState:
        """Format retrieval response for SEARCH intent"""
        chunks = state.get("retrieved_chunks", [])
        formatted = "\n\n".join([
            f"[{c.get('source', 'Unknown')}]: {c.get('content', '')}"
            for c in chunks
        ])
        state["agent_outputs"]["retriever"] = formatted or "No results found"
        state["agents_used"].append("retriever")
        return state

    async def save_memory(self, state: OrchestratorState) -> OrchestratorState:
        """Save context to Memory - direct function call"""
        try:
            user_id = int(state["user_id"]) if state["user_id"].isdigit() else 1
            await store_memory(
                user_id=user_id,
                memory_type="conversation",
                content=state["user_message"],
                session_id=state["session_id"],
                metadata={
                    "response": state.get("final_response", ""),
                    "agents_used": state["agents_used"],
                    "intent": state.get("intent")
                }
            )
            logger.info("Memory context saved")
        except Exception as e:
            logger.error(f"Memory save error: {e}")

        return state

    async def format_final_response(self, state: OrchestratorState) -> OrchestratorState:
        """Format the final response from all agent outputs"""
        outputs = state.get("agent_outputs", {})

        parts = []
        if "tutor" in outputs:
            parts.append(outputs["tutor"])
        elif "planner" in outputs:
            parts.append(outputs["planner"])
        elif "evaluator" in outputs:
            parts.append(outputs["evaluator"])
        elif "retriever" in outputs:
            parts.append(outputs["retriever"])

        if outputs.get("motivator"):
            parts.append(f"\n\n{outputs['motivator']}")

        state["final_response"] = "\n\n".join(parts)
        return state

    def route_by_intent(self, state: OrchestratorState) -> str:
        """Conditional routing based on intent"""
        intent = state.get("intent", "MULTI")

        routing = {
            Intent.EXPLAIN: "run_tutor",
            Intent.STUDY_PLAN: "run_planner",
            Intent.QUIZ_ME: "run_evaluator_quiz",
            Intent.GRADE: "run_evaluator_quiz",
            Intent.MOTIVATE: "run_motivator",
            Intent.SEARCH: "format_retrieval_response",
            Intent.MULTI: "run_parallel_agents"
        }

        return routing.get(intent, "run_parallel_agents")

    def get_compiled(self):
        """Return the compiled graph, building it once on first call."""
        if self._compiled is None:
            self._compiled = self.build_graph().compile()
        return self._compiled

    def build_graph(self) -> StateGraph:
        """Build the LangGraph"""
        graph = StateGraph(OrchestratorState)

        graph.add_node("load_memory", self.load_memory)
        graph.add_node("retrieve_chunks", self.retrieve_chunks)
        graph.add_node("classify_intent", self.classify_intent)
        graph.add_node("run_tutor", self.run_tutor)
        graph.add_node("run_planner", self.run_planner)
        graph.add_node("run_evaluator_quiz", self.run_evaluator_quiz)
        graph.add_node("run_motivator", self.run_motivator)
        graph.add_node("run_parallel_agents", self.run_parallel_agents)
        graph.add_node("format_retrieval_response", self.format_retrieval_response)
        graph.add_node("save_memory", self.save_memory)
        graph.add_node("format_final_response", self.format_final_response)

        graph.set_entry_point("load_memory")
        graph.add_edge("load_memory", "retrieve_chunks")
        graph.add_edge("retrieve_chunks", "classify_intent")

        # Conditional routing
        graph.add_conditional_edges(
            "classify_intent",
            self.route_by_intent,
            {
                "run_tutor": "run_tutor",
                "run_planner": "run_planner",
                "run_evaluator_quiz": "run_evaluator_quiz",
                "run_motivator": "run_motivator",
                "format_retrieval_response": "format_retrieval_response",
                "run_parallel_agents": "run_parallel_agents"
            }
        )

        # All routes lead to save_memory -> format_final_response -> END
        for node in ["run_tutor", "run_planner", "run_evaluator_quiz", "run_motivator", "format_retrieval_response", "run_parallel_agents"]:
            graph.add_edge(node, "save_memory")

        graph.add_edge("save_memory", "format_final_response")
        graph.add_edge("format_final_response", END)

        return graph


# Global orchestrator instance
_orchestrator: Optional[OrchestratorGraph] = None


def get_orchestrator() -> OrchestratorGraph:
    """Get or create the orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorGraph()
    return _orchestrator


async def run_orchestrator(
    task_id: str,
    user_id: str,
    session_id: str,
    user_message: str,
    notebook_id: Optional[str] = None,
    learning_mode: str = "MASTER_THIS"
) -> Dict[str, Any]:
    """Main entry point for orchestrator"""
    orchestrator = get_orchestrator()

    initial_state: OrchestratorState = {
        "task_id": task_id,
        "user_id": user_id,
        "session_id": session_id,
        "user_message": user_message,
        "notebook_id": notebook_id,
        "learning_mode": learning_mode,
        "intent": None,
        "confidence": None,
        "retrieved_chunks": None,
        "memory_context": None,
        "agent_outputs": {},
        "final_response": None,
        "agents_used": [],
        "error": None
    }

    result = await orchestrator.get_compiled().ainvoke(initial_state)

    return {
        "response": result.get("final_response", ""),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "agents_used": result.get("agents_used", []),
        "error": result.get("error")
    }


def get_orchestrator_graph():
    """Get the compiled orchestrator graph (cached)."""
    return get_orchestrator().get_compiled()