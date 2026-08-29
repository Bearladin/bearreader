import contextlib
import io
import logging
import threading
import types
from typing import Any, Callable, Set, Union
import weakref

_Listener = Callable[[str], Any]
_ListenerRef = weakref.ref[_Listener]


class LogSink:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._listeners: Set[_ListenerRef] = set()

    def _discard(self, ref: _ListenerRef):
        with self._lock:
            self._listeners.discard(ref)

    def _make_ref(self, listener: _Listener) -> _ListenerRef:
        if isinstance(listener, types.MethodType):
            return weakref.WeakMethod(listener, self._discard)
        return weakref.ref(listener, self._discard)

    def _all_listeners(self):
        with self._lock:
            values = (ref() for ref in self._listeners)
        return list(filter(None, values))

    def emit(self, record: str):
        for listener in self._all_listeners():
            with contextlib.suppress(Exception):
                listener(record)

    def attach(self, listener: _Listener):
        ref = self._make_ref(listener)
        with self._lock:
            self._listeners.add(ref)

    def detach(self, listener: _Listener):
        with self._lock:
            self._listeners = {ref for ref in self._listeners if ref() is not listener}

    @contextlib.contextmanager
    def pipe(self, listener: _Listener):
        ref = self._make_ref(listener)
        try:
            with self._lock:
                self._listeners.add(ref)
            yield
        finally:
            with contextlib.suppress(Exception):
                with self._lock:
                    self._listeners.remove(ref)

    def handler(self, level: Union[int, str] = 0):
        stream = _LogSinkStream(self)
        h = logging.StreamHandler(stream)
        h.setLevel(level)
        return h

    def print(self, *values, sep=" ", end="\n", **kwargs):
        self.emit(sep.join([str(v) for v in values]) + end)


class _LogSinkStream(io.StringIO):
    def __init__(self, sink: LogSink) -> None:
        self.sink = sink

    def write(self, s: str) -> int:
        self.sink.emit(s)
        return len(s)


def replace_logger(module: types.ModuleType) -> LogSink:
    file = module.__file__
    assert isinstance(file, str)

    queue = LogSink()
    logger = logging.getLogger(str(file))
    logger.handlers = [queue.handler(logger.level)]

    setattr(module, "print", queue.print)
    for attr in dir(module):
        if isinstance(getattr(module, attr), logging.Logger):
            setattr(module, attr, logger)

    setattr(module, "__logs__", queue)
    return queue
