from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime

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
