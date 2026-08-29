from functools import cache
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def browser_intercept() -> Path:
    """
    Returns the path to the browser_intercept.js file.
    """
    return SCRIPTS_DIR / "browser_intercept.js"


@cache
def browser_intercept_script() -> str:
    """
    Returns content of the browser_intercept.js file.
    """
    return browser_intercept().read_text(encoding="utf-8")
