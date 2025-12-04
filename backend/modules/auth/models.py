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

class TokenResponse(BaseModel):
    access_token: str
    session_id: str
    token_type: str = "bearer"
  
class GoogleAuthRequest(BaseModel):
    id_token: str
    is_signup: bool = False
    
class MSAuthRequest(BaseModel):
    id_token: str
    is_signup: bool = False