from pydantic import BaseModel
from typing import Literal, Dict, Any

class GameEvent(BaseModel):
    event_type: Literal["QUESTION", "ANSWER", "RESULT", "LOG", "STATE_UPDATE"]
    payload: Dict[str, Any]
