from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    firstname: str
    lastname: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    token: Optional[str] = Field(default=None)

class TokenResponse(BaseModel):
    access_token: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None)
    two_factor_enabled: Optional[bool] = Field(default=False)
    token_type: str = "bearer"
  
class GoogleAuthRequest(BaseModel):
    id_token: str
    is_signup: bool = False
    
class MSAuthRequest(BaseModel):
    id_token: str
    is_signup: bool = False