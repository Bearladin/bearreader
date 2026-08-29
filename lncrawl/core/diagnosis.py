"""What a scraper failure means *here*, in terms an operator can act on.

The scraper says what happened and what the binding detection layer reads. Neither
sentence knows what this application can offer, so neither can finish the thought — and
"what would help" is the only part of a diagnosis a person can act on. That is the split:
:mod:`scraper.failure` owns the objective half, and every string below names something
lncrawl actually has — a crawler setting, a proxy list, a browser toggle. A library
asserting them would be wrong for the next consumer.

Two functions rather than one on purpose. :func:`describe` is Chinese prose for a person,
:func:`diagnosis_extra` keeps the scraper's stable fields and raw detail for the API. This
also lets a localized client reconstruct old English records without parsing their prose.
"""

import re
from typing import Any, Dict, Optional

from scraper import (
    LAYERS,
    Stance,
    blocking_layer,
    failure_kind,
    is_permanent,
    status_code,
)
from scraper.failure import (
    ABORTED,
    BAD_IMAGE,
    BLOCKED,
    EXHAUSTED,
    FAILED,
    HTTP_ERROR,
    IMPASSABLE,
    MISSING_DEPENDENCY,
    POISONED,
    RENDER_FAILED,
    SOLVE_FAILED,
    TIER_UNAVAILABLE,
    UNREACHABLE,
)

# Reader-facing text belongs here rather than in the general-purpose scraper package. The
# stable failure kind, status, layer and stance are enough to build a Chinese explanation;
# the raw third-party detail remains in Job.extra and the traceback for debugging.
_HEADLINE = {
    IMPASSABLE: "站点要求无法由抓取器伪造的凭据",
    EXHAUSTED: "当前配置可用的重试与绕过方式均已尝试，但请求仍未成功",
    BLOCKED: "站点拒绝了本次请求",
    UNREACHABLE: "请求未能到达站点或未收到响应",
    POISONED: "站点返回了疑似无效或诱导内容",
    TIER_UNAVAILABLE: "当前配置没有可处理此请求的抓取能力",
    MISSING_DEPENDENCY: "处理此请求所需的可选组件尚未安装",
    RENDER_FAILED: "浏览器已打开页面，但未出现书源需要的内容",
    SOLVE_FAILED: "浏览器未能完成站点验证",
    HTTP_ERROR: "站点返回了错误响应",
    BAD_IMAGE: "站点返回的图片内容无法解析",
    ABORTED: "请求已中止",
    FAILED: "请求执行失败",
}

_STATUS_NOTE = {
    404: "页面不存在，通常表示该书源的网址规则已经变化。",
    410: "站点明确表示该页面已永久删除。",
    451: "站点因法律原因拒绝提供该页面。",
}

_ADVICE = {
    RENDER_FAILED: (
        "可能是书源等待的页面元素没有出现、选择器已经失效，或页面加载时间超过浏览器渲染时限。"
    ),
    SOLVE_FAILED: ("请确认已安装可用浏览器、浏览器窗口能够正常启动，并为验证过程预留足够时间。"),
    MISSING_DEPENDENCY: "请检查是否使用完整依赖安装，并重新安装缺失的可选组件。",
    TIER_UNAVAILABLE: "请检查浏览器抓取、代理和归档读取等能力是否已正确配置。",
    BAD_IMAGE: "请稍后重试；若持续出现，通常需要修正书源的图片地址或解析规则。",
    POISONED: "为避免保存错误内容，本次结果已拒绝；请改用其他书源或等待书源修复。",
}

_REMEDY = {
    Stance.SATISFY: ("需要调整抓取器生成的请求签名，这不是用户设置可以解决的问题。"),
    Stance.LEASE: ("只有更换网络出口才可能解决；可在抓取设置中配置代理或 Tor 地址池。"),
    Stance.ACCUMULATE: ("站点正在根据访问历史判断请求；应降低该书源的访问频率，更换地址通常无效。"),
    Stance.SOLVE: ("需要真实浏览器完成验证；请确认浏览器抓取已启用并且本机已安装浏览器。"),
    Stance.AVOID: "该请求触发了本可避免的限制，需要修改书源请求方式。",
    Stance.DELEGATE: ("继续处理需要当前应用未集成的外部付费服务，因此没有可用的本地设置。"),
    Stance.REFUSE: "此内容需要有效账号凭据或已注册的访问身份，无法通过技术绕过。",
}

_ATTEMPT_COUNT = re.compile(r"gave up after (\d+) attempts?", re.IGNORECASE)


def _target(error: BaseException, url: str) -> str:
    return url or getattr(error, "url", "") or ""


def _attempt_count(error: BaseException) -> Optional[int]:
    detail = getattr(error, "detail", "") or ""
    match = _ATTEMPT_COUNT.search(detail)
    return int(match.group(1)) if match else None


def _diagnostic_detail(error: BaseException, kind: str, has_layer: bool) -> Optional[str]:
    detail = getattr(error, "detail", "") or ""
    attempts = _attempt_count(error)
    count = f"连续 {attempts} 次请求" if attempts else "请求"

    if kind == EXHAUSTED and "timeout" in detail.lower():
        suffix = "，也未识别到明确的站点防护层" if not has_layer else ""
        return f"{count}均超时，未收到 HTTP 状态码{suffix}。"
    if kind == EXHAUSTED:
        suffix = "，但未识别到明确的站点防护层" if not has_layer else ""
        return f"{count}均未取得可用响应{suffix}。"
    if kind == UNREACHABLE:
        return "连接可能被本机网络、DNS、代理设置或站点临时故障中断。"
    return None


def describe(error: BaseException, *, url: str = "") -> str:
    """Return a Chinese reader-facing diagnosis without exposing an English traceback."""
    kind = failure_kind(error)
    code = status_code(error)
    first = _HEADLINE.get(kind, _HEADLINE[FAILED])
    if code is not None:
        first += f"（HTTP {code}）"
    target = _target(error, url)
    if target:
        first += f"：{target}"
    parts = [first]

    layer = blocking_layer(error)
    facts = LAYERS.get(layer) if layer is not None else None
    detail = _diagnostic_detail(error, kind, facts is not None)
    if detail:
        parts.append(detail)

    note = _STATUS_NOTE.get(code) if code is not None else None
    if note:
        parts.append(note)

    if facts is not None:
        assert layer is not None
        parts.append(f"检测到第 {int(layer)} 层站点防护。{_REMEDY[facts.stance]}")
    elif kind in (EXHAUSTED, BLOCKED, UNREACHABLE):
        parts.append(
            "请检查本机网络、DNS 和代理设置，或稍后重试；若其他网站正常，也可能是该站点暂时不可用。"
        )

    advice = _ADVICE.get(failure_kind(error))
    if advice:
        parts.append(advice)

    return "\n".join(parts)


def diagnosis_extra(error: BaseException) -> Dict[str, Any]:
    """Structured fields for `Job.extra`, so nothing has to parse the prose."""
    layer = blocking_layer(error)
    facts = LAYERS.get(layer) if layer is not None else None
    return {
        "failure_kind": failure_kind(error),
        "failure_detail": getattr(error, "detail", "") or str(error),
        "failure_url": getattr(error, "url", "") or "",
        "status_code": status_code(error),
        "is_permanent": is_permanent(error),
        "blocking_layer": int(layer) if layer is not None else None,
        "blocking_layer_name": str(layer) if layer is not None else None,
        "reads": facts.trait.value if facts is not None else None,
        "stance": facts.stance.value if facts is not None else None,
    }
