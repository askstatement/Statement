from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime

class UserModel(BaseModel):
    firstname: Optional[str] = Field(default=None)
    lastname: Optional[str] = Field(default=None)
    email: str = Field(default=None)
    hashed_password: Optional[str] = Field(default=None)
    email_token: Optional[str] = Field(default=None)
    email_token_expiry: Optional[datetime] = Field(default=None)
    archived: Optional[bool] = Field(default=False)
    is_email_verified: Optional[bool] = Field(default=False)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    subscription: Optional[dict] = Field(default={
        "plan_slug": "free"
    })

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.updated_at = datetime.utcnow()

class UserProjects(BaseModel):
    name: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    archived: Optional[bool] = Field(default=False)
    credits_allowed: Optional[int] = Field(default=0)
    credits_used: Optional[int] = Field(default=0)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.updated_at = datetime.utcnow()

class ProjectCreateRequest(BaseModel):
    name: Optional[str] = Field(default=None),
    archived: Optional[bool] = Field(default=False)
    
class UserConversation(BaseModel):
    name: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None)
    insight_id: Optional[str] = Field(default=None)
    reason: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    archived: Optional[bool] = Field(default=False)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.updated_at = datetime.utcnow()
        
class InsightsData(BaseModel):
    project_id: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    explanation: Optional[str] = Field(default=None)
    display_type: Optional[Literal['insight', 'graph']] = None
    graph_type: Optional[str] = Field(default=None)
    graph_data: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.updated_at = datetime.utcnow()

class UserPlans(BaseModel):
    name: str = Field(default=None)
    slug: str = Field(default=None)
    description: str = Field(default="")
    price_monthly: Optional[float] = Field(default=0.0)
    price_yearly: Optional[float] = Field(default=0.0)
    monthly_credits_per_project: Optional[int] = Field(default=0)
    project_limit: Optional[int] = Field(default=1)
    features: Optional[List[str]] = Field(default=[])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)