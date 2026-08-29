from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ...enums import FeedbackStatus, FeedbackType


class Feedback(BaseModel):
    """A feedback entry backed by a GitHub issue."""

    id: str = Field(description="GitHub issue number")
    type: FeedbackType = Field(description="Type of feedback")
    status: FeedbackStatus = Field(description="Current status of the feedback")
    subject: str = Field(description="Subject/title of the feedback")
    message: str = Field(description="Detailed message/description")
    created_at: int = Field(description="Creation time (UNIX milliseconds)")
    updated_at: int = Field(description="Last update time (UNIX milliseconds)")
    html_url: str = Field(description="Link to the GitHub issue")
    is_mine: bool = Field(default=False, description="Whether the current user owns this feedback")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FeedbackCreateRequest(BaseModel):
    type: FeedbackType = Field(description="Type of feedback")
    subject: str = Field(description="Subject/title of the feedback", min_length=1, max_length=200)
    message: Optional[str] = Field(
        default=None, description="Detailed message/description", max_length=60000
    )
    extra: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata in JSON format"
    )


class FeedbackUpdateRequest(BaseModel):
    type: Optional[FeedbackType] = Field(default=None, description="Type of feedback")
    subject: Optional[str] = Field(
        default=None, description="Subject/title of the feedback", min_length=1, max_length=200
    )
    message: Optional[str] = Field(
        default=None, description="Detailed message/description", max_length=60000
    )


class FeedbackRespondRequest(BaseModel):
    status: FeedbackStatus = Field(description="Status of the feedback")
