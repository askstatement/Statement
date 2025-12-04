from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PreferencesUpdate(BaseModel):
    twoFactorEnabled: Optional[bool] = None
    notifyResponses: Optional[bool] = None
    notifyTaskUpdate: Optional[bool] = None
