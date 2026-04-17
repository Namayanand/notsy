from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class EmbedResourceRequest(BaseModel):
    resource_id: int
    topic_id: int
    file_path: Optional[str] = None
    source_url: Optional[str] = None
    file_type: str  # pdf, image, video, link, text
    user_id: int


class EmbedStatusResponse(BaseModel):
    resource_id: int
    status: str
    chunk_count: Optional[int] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    topic_id: int
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    learning_mode: str = "MASTER_THIS"  # GO_CRAZY, DEV_MODE, MASTER_THIS, LAST_MINUTE, TEACH_ME_TECH, STUDY_GROUP
    use_web_search: Optional[bool] = False
    explain_depth: Optional[str] = None  # None, "eli5", "deep"
    system_prompt: Optional[str] = None  # For branch context injection


class SourceData(BaseModel):
    filename: str
    chunk: str
    score: float


class ChatResponse(BaseModel):
    response: str
    sources: List[SourceData] = Field(default_factory=list)
    tokens_used: int = 0


class TopicData(BaseModel):
    id: int
    title: str
    description: Optional[str] = None


class GenerateGraphRequest(BaseModel):
    notebook_id: int
    topics: List[TopicData]


class RelationData(BaseModel):
    source_topic_id: int
    target_topic_id: int
    relationship_type: str  # RELATED, PREREQUISITE, EXTENDS, CONTRASTS
    strength: float = 0.5
    description: Optional[str] = None


class GenerateGraphResponse(BaseModel):
    relations: List[RelationData]


class EmbedCallbackRequest(BaseModel):
    resource_id: int
    status: str  # DONE, FAILED
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None
