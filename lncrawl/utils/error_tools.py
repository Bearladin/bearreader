"""Splitting an exception into the part a reader needs and the part a debugger needs.

Both halves are kept in full. A job used to store its stack and its message in one
string, which left every reader — the failure email, the web UI — guessing which line
of it to show, and each of them guessed the last one. Separating them is a change of
shape, not of content: nothing here summarises, truncates or redacts.
"""

import traceback
from typing import Optional


def full_traceback(error: BaseException) -> str:
    """The complete stack behind *error*, exactly as Python formats it."""
    lines = traceback.format_exception(
        type(error),
        value=error,
        tb=error.__traceback__,
        chain=True,
    )
    return "".join(lines).strip()


def unexpected_message(error: BaseException, kind: Optional[str] = None) -> str:
    """A Chinese reader-facing line for a failure nothing anticipated.

    The exception and complete traceback remain in ``Job.extra`` for diagnosis, so the
    visible message does not need to leak an untranslated third-party error.
    """
    del error, kind
    return "任务因程序内部异常而停止。这属于应用或书源程序问题，不是网站拒绝请求；请提交问题反馈。"
