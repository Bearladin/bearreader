from fastapi import APIRouter, Body, Path, Query, Security

from ...context import ctx
from ...dao import FeedbackStatus, FeedbackType, User
from ...server.models import (
    Feedback,
    FeedbackCreateRequest,
    FeedbackRespondRequest,
    FeedbackUpdateRequest,
    Paginated,
)
from ..security import ensure_user

# The root router
router = APIRouter()


@router.get("s", summary="Get list of feedbacks")
def list_feedback(
    user: User = Security(ensure_user),
    search: str = Query(default=""),
    status: FeedbackStatus = Query(default=None),
    type: FeedbackType = Query(default=None),
    mine: bool = Query(default=False, description="Only show feedback submitted by the user"),
    offset: int = Query(default=0),
    limit: int = Query(default=20, le=100),
) -> Paginated[Feedback]:
    return ctx.feedback.list(
        user=user,
        offset=offset,
        limit=limit,
        search=search,
        status=status,
        type=type,
        mine=mine,
    )


@router.post("", summary="Submit feedback")
def create_feedback(
    user: User = Security(ensure_user),
    body: FeedbackCreateRequest = Body(
        default=...,
        description="The feedback",
    ),
) -> Feedback:
    return ctx.feedback.create(
        user=user,
        type=body.type,
        subject=body.subject,
        message=body.message or "",
        extra=body.extra or {},
    )


@router.get("/{feedback_id}", summary="Get feedback by ID")
def get_feedback(
    feedback_id: str = Path(),
    user: User = Security(ensure_user),
) -> Feedback:
    return ctx.feedback.get(user, feedback_id)


@router.put("/{feedback_id}", summary="Update feedback")
def update_feedback(
    feedback_id: str = Path(),
    user: User = Security(ensure_user),
    body: FeedbackUpdateRequest = Body(
        default=...,
        description="The feedback update",
    ),
) -> Feedback:
    return ctx.feedback.update(
        user=user,
        feedback_id=feedback_id,
        type=body.type,
        subject=body.subject,
        message=body.message,
    )


@router.post("/{feedback_id}/respond", summary="Respond to feedback")
def respond_to_feedback(
    feedback_id: str = Path(),
    user: User = Security(ensure_user),
    body: FeedbackRespondRequest = Body(
        default=...,
        description="The feedback response",
    ),
) -> Feedback:
    return ctx.feedback.respond(
        user=user,
        feedback_id=feedback_id,
        status=body.status,
    )


@router.delete("/{feedback_id}", summary="Delete feedback")
def delete_feedback(
    feedback_id: str = Path(),
    user: User = Security(ensure_user),
) -> bool:
    return ctx.feedback.delete(
        user=user,
        feedback_id=feedback_id,
    )
