from difflib import SequenceMatcher
from typing import Any, Callable, List, Optional, TypeVar

T = TypeVar("T")


def binary_search(
    items: List[Any],
    target: Any,
    compare: Callable[[Any, Any], bool],
):
    left = 0
    right = len(items) - 1
    while left <= right:
        mid = (left + right) // 2
        if compare(items[mid], target):
            left = mid + 1
        elif compare(target, items[mid]):
            right = mid - 1
        else:
            return mid
    return None


def sort_by_rank(
    items: List[T],
    query: str,
    key: Optional[Callable[[T], Any]],
    reverse: bool = False,
):
    if not key:
        key = str
    items.sort(
        reverse=not reverse,
        key=lambda x: SequenceMatcher(
            a=key(x),
            b=query,
        ).ratio(),
    )
