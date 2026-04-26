"""A2A Agent Card models following Google's Agent-to-Agent protocol specification"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class AgentCapabilities(BaseModel):
    """Agent capabilities as defined in A2A protocol"""
    streaming: bool = True
    stateTransitionHistory: bool = True


class AgentSkill(BaseModel):
    """Agent skill definition as defined in A2A protocol"""
    id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Human-readable skill name")
    description: str = Field(..., description="What the skill does")
    inputModes: List[str] = Field(default_factory=lambda: ["text"], description="Accepted input formats")
    outputModes: List[str] = Field(default_factory=lambda: ["text"], description="Output formats")


class AgentCard(BaseModel):
    """Agent Card as defined in A2A protocol - exposes agent metadata at /.well-known/agent.json"""
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    version: str = Field(default="1.0.0", description="Semantic version")
    url: str = Field(..., description="Agent endpoint URL")
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    skills: List[AgentSkill] = Field(default_factory=list, description="List of skills the agent supports")


# Predefined skill definitions for each agent type
PLANNER_SKILLS = [
    AgentSkill(
        id="generate_study_plan",
        name="Generate Study Plan",
        description="Creates a structured learning roadmap based on user goals",
        inputModes=["text"],
        outputModes=["text"]
    ),
    AgentSkill(
        id="break_topic_into_subtopics",
        name="Break Topic Into Subtopics",
        description="Decomposes a complex topic into learnable subtopics",
        inputModes=["text"],
        outputModes=["text"]
    ),
]

TUTOR_SKILLS = [
    AgentSkill(
        id="explain_concept",
        name="Explain Concept",
        description="Explains a concept using RAG over uploaded study materials",
        inputModes=["text"],
        outputModes=["text"]
    ),
    AgentSkill(
        id="answer_question",
        name="Answer Question",
        description="Answers a specific question with context from knowledge base",
        inputModes=["text"],
        outputModes=["text"]
    ),
    AgentSkill(
        id="summarize_topic",
        name="Summarize Topic",
        description="Provides a concise summary of a topic",
        inputModes=["text"],
        outputModes=["text"]
    ),
]

EVALUATOR_SKILLS = [
    AgentSkill(
        id="grade_quiz",
        name="Grade Quiz",
        description="Generates and grades quiz questions",
        inputModes=["text"],
        outputModes=["text"]
    ),
    AgentSkill(
        id="score_flashcard",
        name="Score Flashcard",
        description="Evaluates flashcard responses",
        inputModes=["text"],
        outputModes=["text"]
    ),
    AgentSkill(
        id="give_feedback",
        name="Give Feedback",
        description="Provides feedback on learning progress",
        inputModes=["text"],
        outputModes=["text"]
    ),
]

MOTIVATOR_SKILLS = [
    AgentSkill(
        id="generate_encouragement",
        name="Generate Encouragement",
        description="Generates personalized motivational messages",
        inputModes=["text"],
        outputModes=["text"]
    ),
    AgentSkill(
        id="track_streak_milestone",
        name="Track Streak Milestone",
        description="Tracks learning streaks and celebrates milestones",
        inputModes=["text"],
        outputModes=["text"]
    ),
]

RETRIEVER_SKILLS = [
    AgentSkill(
        id="semantic_search",
        name="Semantic Search",
        description="Performs semantic search over knowledge base",
        inputModes=["text"],
        outputModes=["text"]
    ),
    AgentSkill(
        id="fetch_relevant_chunks",
        name="Fetch Relevant Chunks",
        description="Retrieves relevant content chunks from ChromaDB",
        inputModes=["text"],
        outputModes=["text"]
    ),
]

MEMORY_SKILLS = [
    AgentSkill(
        id="store_context",
        name="Store Context",
        description="Stores conversation context for later retrieval",
        inputModes=["text"],
        outputModes=["text"]
    ),
    AgentSkill(
        id="retrieve_context",
        name="Retrieve Context",
        description="Retrieves stored conversation context",
        inputModes=["text"],
        outputModes=["text"]
    ),
    AgentSkill(
        id="summarize_history",
        name="Summarize History",
        description="Summarizes conversation history",
        inputModes=["text"],
        outputModes=["text"]
    ),
]

ORCHESTRATOR_SKILLS = [
    AgentSkill(
        id="auto",
        name="Auto Route",
        description="Automatically routes user request to appropriate agent",
        inputModes=["text"],
        outputModes=["text", "streaming"]
    ),
]