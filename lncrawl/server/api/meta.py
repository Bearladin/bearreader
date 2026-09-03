from typing import List

from fastapi import APIRouter, Query, Security
from fastapi.responses import JSONResponse
from pydantic import HttpUrl
from starlette.responses import FileResponse

from ...context import ctx
from ..models import SourceItem
from ..security import ensure_user

# The root router
router = APIRouter()


@router.get(
    "/supported-sources",
    summary="Returns a list of supported sources",
    dependencies=[Security(ensure_user)],
    response_model=List[SourceItem],
)
def list_supported_sources():
    result = ctx.sources.list(include_rejected=True)
    return JSONResponse(
        content=[item.model_dump() for item in result],
        headers={
            "ETag": str(ctx.sources.version),
            # The desktop browser profile survives portable upgrades and every
            # build normally reuses localhost:31580. A fresh max-age response
            # therefore hid newly bundled sources for four hours after an
            # upgrade. The list is small and local, so never store it.
            "Cache-Control": "private, no-store",
        },
    )


@router.get(
    "/favicon",
    summary="Get favicon of a site",
)
def get_favicon(
    url: HttpUrl = Query(description="URL"),
) -> FileResponse:
    file = ctx.http.favicon(str(url))
    return FileResponse(
        file,
        filename="favicon.ico",
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
