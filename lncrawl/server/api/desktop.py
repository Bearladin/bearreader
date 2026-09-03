from fastapi import APIRouter, Body

from ...context import ctx
from ..models import OpenExternalRequest

router = APIRouter()


@router.post("/open-external", summary="Open an external web URL in the system browser")
def open_external(body: OpenExternalRequest = Body()) -> bool:
    ctx.desktop.open_external(body.url)
    return True
