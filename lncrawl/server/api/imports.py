from typing import Optional

from fastapi import APIRouter, Body, File, Path, Security, UploadFile

from ...context import ctx
from ...dao import User
from ...server.models import (
    EpubImportCommitRequest,
    EpubImportSessionResponse,
    EpubImportStartResponse,
)
from ..security import ensure_user

router = APIRouter()


@router.post("/epub", response_model=EpubImportStartResponse)
async def start_epub_import(
    file: UploadFile = File(...),
    user: User = Security(ensure_user),
) -> EpubImportStartResponse:
    result = await ctx.epub_import.start_upload(user, file)
    return EpubImportStartResponse(**result)


@router.get(
    "/epub/{session_id}",
    response_model=EpubImportSessionResponse,
)
def get_epub_import(
    session_id: str = Path(),
    user: User = Security(ensure_user),
) -> EpubImportSessionResponse:
    return EpubImportSessionResponse(**ctx.epub_import.session_view(session_id, user))


@router.post(
    "/epub/{session_id}/commit",
    response_model=EpubImportStartResponse,
)
def commit_epub_import(
    session_id: str = Path(),
    body: Optional[EpubImportCommitRequest] = Body(default=None),
    user: User = Security(ensure_user),
) -> EpubImportStartResponse:
    title = body.title if body and body.title is not None else ""
    authors = body.authors if body and body.authors is not None else ""
    job = ctx.epub_import.claim_commit(session_id, user, title, authors)
    return EpubImportStartResponse(session_id=session_id, job_id=job.id)


@router.post("/epub/{session_id}/cancel")
def cancel_epub_import(
    session_id: str = Path(),
    user: User = Security(ensure_user),
) -> bool:
    ctx.epub_import.cancel(session_id, user)
    return True
