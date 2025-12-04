from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Any, Dict

class PromptData(BaseModel):
    user_id: Optional[str] = Field(default=None)
    conversation_id: Optional[str] = Field(default=None)
    model: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None)
    type: Optional[Literal['prompt', 'response', 'file_upload']] = None
    content: Optional[str] = Field(default=None)
    followup: Optional[str] = Field(default=None)
    graph_data: Optional[dict] = Field(default=None)
    steps: Optional[List] = Field(default=[])
    messages: Optional[List] = Field(default=None)
    token_usage: Optional[dict] = Field(default={})
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.updated_at = datetime.utcnow()

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ResponseSchemaField(BaseModel):
    type: Literal["object", "array", "string", "number", "boolean", "null"]
    properties: Optional[Dict[str, Any]] = None
    items: Optional[Any] = None
    required: Optional[List[str]] = None
    description: Optional[str] = None
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field(None, description="The model to use for generating responses.")
    messages: List[Message] = Field(..., description="List of conversation messages.")
    response_schema: Optional[ResponseSchemaField] = Field(
        None, description="Optional JSON schema for structured responses."
    )


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    created: int
    usage: Optional[dict] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0
    }
    choices: List[dict]