"""Edge-TTS 在线朗读服务（v1.1.8，在线轨）。

使用微软 Edge 内置的神经语音接口（edge-tts，LGPLv3，许可证文本随包分发）。
仅提供内置中文音色白名单（普通话 6 + 台湾国语 3）；合成必须联网，
失败时抛出 ValueError，由路由层转为 503 提示。

服务无持久连接、无后台线程，因此不需要 destroy()。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# 内置音色白名单。固定返回（不依赖联网拉取），
# 保持列表稳定且与"只保留普通话+台湾国语"的产品决策一致。
VOICES: Tuple[dict, ...] = (
    {
        "id": "zh-CN-XiaoxiaoNeural",
        "name": "晓晓",
        "locale": "普通话",
        "gender": "女",
        "style": "温暖，适合小说朗读",
    },
    {
        "id": "zh-CN-XiaoyiNeural",
        "name": "晓伊",
        "locale": "普通话",
        "gender": "女",
        "style": "活泼",
    },
    {
        "id": "zh-CN-YunjianNeural",
        "name": "云健",
        "locale": "普通话",
        "gender": "男",
        "style": "激情",
    },
    {
        "id": "zh-CN-YunxiNeural",
        "name": "云希",
        "locale": "普通话",
        "gender": "男",
        "style": "阳光",
    },
    {
        "id": "zh-CN-YunxiaNeural",
        "name": "云夏",
        "locale": "普通话",
        "gender": "男",
        "style": "可爱",
    },
    {
        "id": "zh-CN-YunyangNeural",
        "name": "云扬",
        "locale": "普通话",
        "gender": "男",
        "style": "专业稳重",
    },
    {
        "id": "zh-TW-HsiaoChenNeural",
        "name": "曉臻",
        "locale": "台湾国语",
        "gender": "女",
        "style": "友好",
    },
    {
        "id": "zh-TW-HsiaoYuNeural",
        "name": "曉雨",
        "locale": "台湾国语",
        "gender": "女",
        "style": "友好",
    },
    {
        "id": "zh-TW-YunJheNeural",
        "name": "雲哲",
        "locale": "台湾国语",
        "gender": "男",
        "style": "友好",
    },
)

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
VOICE_IDS = {v["id"] for v in VOICES}

MIN_RATE = 0.5
MAX_RATE = 1.5

_SENTENCE_TIMEOUT = 20.0  # 单句合成超时（秒）
_CACHE_LIMIT = 512  # 音频 LRU 上限（条）


def _rate_format(rate: float) -> str:
    """0.5 → "-50%"，1.25 → "+25%"（edge-tts 的 SSML prosody rate）。"""
    percent = round((rate - 1.0) * 100)
    return f"{percent:+d}%"


class TtsService:
    """edge-tts 在线合成服务。每句一个独立连接，无状态。"""

    def __init__(self) -> None:
        self._cache: dict[str, bytes] = {}

    def list_voices(self) -> List[dict]:
        return list(VOICES)

    async def synthesize_sentence(
        self, text: str, voice: str = DEFAULT_VOICE, rate: float = 1.0
    ) -> bytes:
        """合成单句文本，返回 mp3 字节。失败抛 ValueError（路由层转 503）。"""
        if text.strip() == "":
            raise ValueError("文本为空")
        cache_key = hashlib.sha1(f"{text}\x00{voice}\x00{rate}".encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        import edge_tts

        communicate = edge_tts.Communicate(text, voice, rate=_rate_format(rate))
        chunks: list[bytes] = []

        async def _collect() -> None:
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    data = chunk.get("data")
                    if data:
                        chunks.append(data)

        try:
            await asyncio.wait_for(_collect(), timeout=_SENTENCE_TIMEOUT)
        except asyncio.TimeoutError:
            raise ValueError(f"语音合成超时（{_SENTENCE_TIMEOUT}s）") from None
        except Exception as exc:  # 网络中断 / 限流 / 接口变动
            logger.warning("edge-tts synthesize failed: %r", exc)
            raise ValueError("语音合成失败，请检查网络后重试") from exc

        audio = b"".join(chunks)
        if not audio:
            raise ValueError("语音合成返回空音频")
        if len(self._cache) >= _CACHE_LIMIT:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = audio
        return audio
