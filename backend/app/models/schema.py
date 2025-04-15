from pydantic import BaseModel, Field, confloat
from typing import List, Optional, Dict, Any, Union

class StoryAction(BaseModel):
    """User action that can be either a choice from options or a custom input."""
    choice: Optional[str] = None
    customInput: Optional[str] = None

class DebugConfig(BaseModel):
    """Configuration for debugging and prompt engineering."""
    storyModel: Optional[str] = None
    summaryModel: Optional[str] = None
    systemPrompt: Optional[str] = None
    summarySystemPrompt: Optional[str] = None
    temperature: Optional[float] = Field(default=0.7, description="Controls randomness of the LLM output. 0 is deterministic, 1 is very random.")

class TaleRequest(BaseModel):
    """Request structure for generating tale segments."""
    taleId: str
    storyHistory: List[str] = []
    currentSummary: str = ""
    currentTurnNumber: int = 0
    action: StoryAction
    debugConfig: Optional[DebugConfig] = None

class LlmJsonResponse(BaseModel):
    """Structure for the expected LLM JSON response."""
    storySegment: str
    choices: List[str]

class TaleResponse(BaseModel):
    """Response structure for tale generation."""
    storySegment: str
    choices: List[str]
    updatedSummary: str
    nextTurnNumber: int
    rawResponse: Optional[Union[str, Dict[str, Any]]] = None