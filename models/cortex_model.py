from pydantic import BaseModel
from typing import List, Optional

class HistoryMessage(BaseModel):
    role: str      # "user" or "assistant"
    content: str

class CortexRequest(BaseModel):
    question: str
    history: Optional[List[HistoryMessage]] = []

class CortexResponse(BaseModel):
    answer: str
    category: str