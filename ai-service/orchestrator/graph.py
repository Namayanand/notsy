"""LangGraph-based orchestrator with intelligent routing"""
import json
import logging
import os
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.constants import START

import httpx

logger = logging.getLogger(__name__)

# Agent endpoints from environment
AGENT_ENDPOINTS = {
    "planner": os.getenv("AGENT_PLANNER_URL", os.getenv("PLANNER_URL", "http://localhost:8001")),
    "tutor": os.getenv("AGENT_TUTOR_URL", os.getenv("TUTOR_URL", "http://localhost:8002")),
    "evaluator": os.getenv("AGENT_EVALUATOR_URL", os.getenv("EVALUATOR_URL", "http://localhost:8003")),
    "motivator": os.getenv("AGENT_MOTIVATOR_URL", os.getenv("MOTIVATOR_URL", "http://localhost:8004")),
    "retriever": os.getenv("AGENT_RETRIEVER_URL", os.getenv("RETRIEVER_URL", "http://localhost:8005")),
    "memory": os.getenv("AGENT_MEMORY_URL", os.getenv("MEMORY_URL", "http://localhost:8006")),
}


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
        self._http_client = None
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3-70b-8192")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()

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
            client = await self._get_client()
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

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                # Parse JSON from response
                parsed = json.loads(content.strip("```json").strip("```").strip())

                intent = parsed.get("intent", "MULTI")
                confidence = parsed.get("confidence", 0.5)

                # Low confidence → MULTI
                if confidence < 0.6:
                    intent = "MULTI"

                state["intent"] = intent
                state["confidence"] = confidence
                logger.info(f"Intent classified: {intent} (confidence: {confidence})")
            else:
                logger.warning(f"Groq classification failed: {response.status_code}")
                state["intent"] = "MULTI"
                state["confidence"] = 0.5

        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            state["intent"] = "MULTI"
            state["confidence"] = 0.5

        return state

    async def load_memory(self, state: OrchestratorState) -> OrchestratorState:
        """Load context from Memory agent"""
        user_id = state["user_id"]
        session_id = state["session_id"]

        try:
            client = await self._get_client()
            response = await client.post(
                f"{AGENT_ENDPOINTS['memory']}/tasks/send",
                json={
                    "taskId": f"{state['task_id']}-memory-load",
                    "skill": {"id": "retrieve_context"},
                    "message": {
                        "role": "user",
                        "content": f"Retrieve context for user {user_id}",
                        "metadata": {
                            "session_id": session_id,
                            "user_id": user_id,
                            "last_n_turns": 5
                        }
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                output = result.get("output", {})
                content = output.get("content", "{}")
                try:
                    context = json.loads(content)
                except:
                    context = {"raw": content}

                state["memory_context"] = context
                logger.info(f"Memory context loaded for user {user_id}")
            else:
                state["memory_context"] = {}
                logger.warning(f"Memory load failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Memory load error: {e}")
            state["memory_context"] = {}

        state["agents_used"].append("memory")
        return state

    async def retrieve_chunks(self, state: OrchestratorState) -> OrchestratorState:
        """Retrieve relevant chunks from Retriever agent"""
        query = state["user_message"]
        notebook_id = state.get("notebook_id")

        try:
            client = await self._get_client()
            response = await client.post(
                f"{AGENT_ENDPOINTS['retriever']}/tasks/send",
                json={
                    "taskId": f"{state['task_id']}-retrieve",
                    "skill": {"id": "semantic_search"},
                    "message": {
                        "role": "user",
                        "content": query,
                        "metadata": {
                            "notebook_id": notebook_id,
                            "top_k": 5,
                            "rerank": True
                        }
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                output = result.get("output", {})
                content = output.get("content", "[]")
                try:
                    chunks = json.loads(content)
                except:
                    chunks = [{"content": content, "source": "unknown"}]

                state["retrieved_chunks"] = chunks
                logger.info(f"Retrieved {len(chunks)} chunks")
            else:
                state["retrieved_chunks"] = []
                logger.warning(f"Retrieval failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            state["retrieved_chunks"] = []

        return state

    async def run_tutor(self, state: OrchestratorState) -> OrchestratorState:
        """Run Tutor agent with RAG context"""
        try:
            client = await self._get_client()
            response = await client.post(
                f"{AGENT_ENDPOINTS['tutor']}/tasks/send",
                json={
                    "taskId": f"{state['task_id']}-tutor",
                    "skill": {"id": "explain_concept"},
                    "message": {
                        "role": "user",
                        "content": state["user_message"],
                        "metadata": {
                            "rag_chunks": state.get("retrieved_chunks", []),
                            "memory": state.get("memory_context", {}),
                            "mode": state.get("learning_mode", "MASTER_THIS")
                        }
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                output = result.get("output", {})
                state["agent_outputs"]["tutor"] = output.get("content", "")
            else:
                state["agent_outputs"]["tutor"] = "Tutor unavailable"

            state["agents_used"].append("tutor")
        except Exception as e:
            logger.error(f"Tutor error: {e}")
            state["agent_outputs"]["tutor"] = f"Error: {str(e)}"

        return state

    async def run_planner(self, state: OrchestratorState) -> OrchestratorState:
        """Run Planner agent with RAG context"""
        try:
            client = await self._get_client()
            memory_context = state.get("memory_context", {})

            response = await client.post(
                f"{AGENT_ENDPOINTS['planner']}/tasks/send",
                json={
                    "taskId": f"{state['task_id']}-planner",
                    "skill": {"id": "generate_study_plan"},
                    "message": {
                        "role": "user",
                        "content": state["user_message"],
                        "metadata": {
                            "rag_chunks": state.get("retrieved_chunks", []),
                            "memory": memory_context,
                            "weak_topics": memory_context.get("weak_topics", [])
                        }
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                output = result.get("output", {})
                state["agent_outputs"]["planner"] = output.get("content", "")
            else:
                state["agent_outputs"]["planner"] = "Planner unavailable"

            state["agents_used"].append("planner")
        except Exception as e:
            logger.error(f"Planner error: {e}")
            state["agent_outputs"]["planner"] = f"Error: {str(e)}"

        return state

    async def run_evaluator_quiz(self, state: OrchestratorState) -> OrchestratorState:
        """Run Evaluator agent for quiz generation"""
        try:
            client = await self._get_client()
            memory_context = state.get("memory_context", {})

            response = await client.post(
                f"{AGENT_ENDPOINTS['evaluator']}/tasks/send",
                json={
                    "taskId": f"{state['task_id']}-evaluator",
                    "skill": {"id": "grade_quiz"},
                    "message": {
                        "role": "user",
                        "content": state["user_message"],
                        "metadata": {
                            "rag_chunks": state.get("retrieved_chunks", []),
                            "memory": memory_context,
                            "num_questions": 5,
                            "difficulty": "adaptive"
                        }
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                output = result.get("output", {})
                state["agent_outputs"]["evaluator"] = output.get("content", "")
            else:
                state["agent_outputs"]["evaluator"] = "Evaluator unavailable"

            state["agents_used"].append("evaluator")
        except Exception as e:
            logger.error(f"Evaluator error: {e}")
            state["agent_outputs"]["evaluator"] = f"Error: {str(e)}"

        return state

    async def run_motivator(self, state: OrchestratorState) -> OrchestratorState:
        """Run Motivator agent"""
        try:
            client = await self._get_client()
            memory_context = state.get("memory_context", {})
            primary_response = state["agent_outputs"].get("tutor") or state["agent_outputs"].get("planner") or state["agent_outputs"].get("evaluator", "")

            response = await client.post(
                f"{AGENT_ENDPOINTS['motivator']}/tasks/send",
                json={
                    "taskId": f"{state['task_id']}-motivator",
                    "skill": {"id": "generate_encouragement"},
                    "message": {
                        "role": "user",
                        "content": "Generate encouragement",
                        "metadata": {
                            "user_message": state["user_message"],
                            "streak_data": memory_context.get("streak", {}),
                            "main_response": primary_response
                        }
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                output = result.get("output", {})
                state["agent_outputs"]["motivator"] = output.get("content", "")
            else:
                state["agent_outputs"]["motivator"] = ""

            state["agents_used"].append("motivator")
        except Exception as e:
            logger.error(f"Motivator error: {e}")
            state["agent_outputs"]["motivator"] = ""

        return state

    async def run_parallel_agents(self, state: OrchestratorState) -> OrchestratorState:
        """Run multiple agents in parallel for MULTI intent"""
        import asyncio

        async def run_all():
            tasks = [
                self.run_tutor(state.copy()),
                self.run_planner(state.copy()),
                self.run_evaluator_quiz(state.copy()),
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            return state

        return await run_all()

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
        """Save context to Memory agent"""
        try:
            client = await self._get_client()
            final_response = state.get("final_response", "")

            await client.post(
                f"{AGENT_ENDPOINTS['memory']}/tasks/send",
                json={
                    "taskId": f"{state['task_id']}-memory-save",
                    "skill": {"id": "store_context"},
                    "message": {
                        "role": "user",
                        "content": "Store context",
                        "metadata": {
                            "user_id": state["user_id"],
                            "session_id": state["session_id"],
                            "user_message": state["user_message"],
                            "final_response": final_response,
                            "agents_used": state["agents_used"],
                            "intent": state.get("intent")
                        }
                    }
                }
            )
            logger.info("Memory context saved")
        except Exception as e:
            logger.error(f"Memory save error: {e}")

        return state

    async def format_final_response(self, state: OrchestratorState) -> OrchestratorState:
        """Format the final response from all agent outputs"""
        outputs = state.get("agent_outputs", {})

        # Build response from all outputs
        parts = []

        # Primary response (tutor, planner, or evaluator)
        if "tutor" in outputs:
            parts.append(outputs["tutor"])
        elif "planner" in outputs:
            parts.append(outputs["planner"])
        elif "evaluator" in outputs:
            parts.append(outputs["evaluator"])
        elif "retriever" in outputs:
            parts.append(outputs["retriever"])

        # Add motivation if present
        if outputs.get("motivator"):
            parts.append(f"\n\n💪 {outputs['motivator']}")

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

    def build_graph(self) -> StateGraph:
        """Build the LangGraph"""
        graph = StateGraph(OrchestratorState)

        # Add all nodes
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

        # Set entry point
        graph.set_entry_point("load_memory")

        # Sequential edges
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
                "run_parallel_agents": "run_parallel_agents",
                "format_retrieval_response": "format_retrieval_response"
            }
        )

        # All primary nodes → motivational → save → format
        for node in ["run_tutor", "run_planner", "run_evaluator_quiz",
                     "run_parallel_agents", "format_retrieval_response"]:
            graph.add_edge(node, "run_motivator")

        graph.add_edge("run_motivator", "save_memory")
        graph.add_edge("save_memory", "format_final_response")
        graph.add_edge("format_final_response", END)

        return graph


# Global orchestrator instance
_orchestrator_graph: Optional[OrchestratorGraph] = None


def get_orchestrator_graph() -> OrchestratorGraph:
    """Get or create the orchestrator graph instance"""
    global _orchestrator_graph
    if _orchestrator_graph is None:
        _orchestrator_graph = OrchestratorGraph()
        _orchestrator_graph._graph = _orchestrator_graph.build_graph().compile()
    return _orchestrator_graph


async def run_orchestrator(
    task_id: str,
    user_id: str,
    session_id: str,
    user_message: str,
    notebook_id: Optional[str] = None,
    learning_mode: str = "MASTER_THIS"
) -> Dict[str, Any]:
    """Run the orchestrator pipeline"""
    orch = get_orchestrator_graph()

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

    try:
        result = await orch._graph.ainvoke(initial_state)
        return {
            "success": True,
            "response": result.get("final_response", ""),
            "agents_used": result.get("agents_used", []),
            "intent": result.get("intent"),
            "confidence": result.get("confidence")
        }
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        return {
            "success": False,
            "error": str(e),
            "response": "I apologize, but I encountered an error processing your request.",
            "agents_used": [],
            "intent": "ERROR",
            "confidence": 0.0
        }