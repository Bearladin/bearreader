from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ...enums import JobStatus


class EpubImportStartResponse(BaseModel):
    session_id: Optional[str] = Field(default=None, description="EPUB import session ID")
    job_id: Optional[str] = Field(default=None, description="Analysis job ID")
    existing_novel_id: Optional[str] = Field(
        default=None,
        description="Existing novel ID when the same EPUB was already imported",
    )


class EpubImportCommitRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200, description="Novel title override")
    authors: Optional[str] = Field(default=None, max_length=200, description="Author override")


class EpubImportSessionResponse(BaseModel):
    id: str
    status: str
    original_name: str
    file_size: int
    expires_at: int
    analyze_job_id: Optional[str] = None
    commit_job_id: Optional[str] = None
    novel_id: Optional[str] = None
    job_status: Optional[JobStatus] = None
    progress: int = 0
    phase: Optional[str] = None
    error: Optional[str] = None
    preview: Optional[Dict[str, Any]] = None


class EpubImportSample(BaseModel):
    title: str
    body_preview: str


class EpubImportPreview(BaseModel):
    title: str
    authors: str
    language: Optional[str] = None
    synopsis: str = ""
    tags: List[str] = []
    chapters: int
    volumes: int
    cover_available: bool
    samples: List[EpubImportSample] = []
