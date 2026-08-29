"""Edge-TTS 在线朗读接口（v1.1.8）。

提供 9 个内置中文音色列表与单句合成接口。合成依赖网络，
失败时以 503 + 中文提示返回（前端据此提示"需要联网"）。
"""

from io import BytesIO

from fastapi import APIRouter, Body, Security
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...context import ctx
from ...dao import User
from ...exceptions import ServerErrors
from ...services.tts import (
    DEFAULT_VOICE,
    MAX_RATE,
    MIN_RATE,
    VOICE_IDS,
)
from ..security import ensure_user

router = APIRouter()


class SynthesizeRequest(BaseModel):
    sentence: str = Field(min_length=1, max_length=2000)
    voice: str = DEFAULT_VOICE
    rate: float = Field(default=1.0, ge=MIN_RATE, le=MAX_RATE)


@router.get("/voices", summary="朗读音色列表（中文）")
def list_voices(user: User = Security(ensure_user)):
    return {
        "voices": ctx.tts.list_voices(),
        "default": DEFAULT_VOICE,
        "min_rate": MIN_RATE,
        "max_rate": MAX_RATE,
    }


@router.post("/synthesize", summary="合成一句语音（mp3）")
async def synthesize(
    request: SynthesizeRequest = Body(...),
    user: User = Security(ensure_user),
):
    # 宽容回退：旧版本持久化的系统语音名不在白名单时，用默认晓晓合成，
    # 而不是 404 让朗读彻底失败（前端设置页会同时归一化旧值）。
    if request.voice not in VOICE_IDS:
        request.voice = DEFAULT_VOICE
    try:
        audio = await ctx.tts.synthesize_sentence(request.sentence, request.voice, request.rate)
    except ValueError as exc:
        raise ServerErrors.service_unavailable.with_extra(str(exc)) from exc
    return StreamingResponse(BytesIO(audio), media_type="audio/mpeg")
