import functools
import inspect
from contextlib import AbstractContextManager
from contextvars import ContextVar
from types import TracebackType
from collections.abc import Callable
from typing import Any, Literal

from opentelemetry import trace as otel_trace

class PassThruTraceContext(AbstractContextManager["PassThruTraceContext"]):
    def __init__(self) -> None:
        ...

    def __enter__(self) -> "PassThruTraceContext":
        return self

    # The name and signature of this function must match that of otel. DO NOT CHANGE
    def set_attribute(self, key: str, val: object) -> None:
        ...

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> Literal[False]:
        return False

# Stateless (no per-call data), so one instance is safely shared across every
# disabled/filtered-out call instead of allocating a new one each time - this
# is the common case at runtime (tracing off or below a call's level).
_PASS_THRU = PassThruTraceContext()

otel_tracer = otel_trace.get_tracer(__name__)

def trace_details_to_max_size(trace_details: int) -> int:
    return 99 + 4**trace_details

def normalize_attribute(value: object, trace_details: int) -> object:
    # Primitive passthrough
    if isinstance(value, (int, float, str, bool)):
        return value
    # Fallback: stringify
    str_val = str(value)
    max_size = trace_details_to_max_size(trace_details)
    if len(str_val) > max_size:
        str_val = str_val[0:max_size] + '...'
    return str_val

_service_context_vars: tuple[ContextVar, ContextVar] | None = None

def _get_context_vars() -> tuple[ContextVar, ContextVar]:
    # Deferred import breaks the service.py <-> tracer.py import cycle
    # (service.py imports `trace` from this module at load time). Cached
    # after the first resolution - the ContextVar objects never change once
    # both modules have finished loading, so there's no need to re-resolve
    # the import on every one of the (potentially millions of) traced calls.
    global _service_context_vars
    if _service_context_vars is None:
        from knowledgenet.service import trace_level, trace_details
        _service_context_vars = (trace_level, trace_details)
    return _service_context_vars

def trace_context_factory(level: int, filter: Callable[[tuple, dict], bool] | None, f_func: Callable, f_args: tuple, f_kwargs: dict, trace_level_val: int, trace_details_val: int) -> AbstractContextManager[Any]:
    filter_pass = filter(f_args, f_kwargs) if filter else True
    to_trace = trace_level_val >= level and filter_pass
    if not to_trace:
        return _PASS_THRU

    object_id: object = None
    name: str | None = None
    # Heuristic: if there is a first arg and it has a callable attribute
    # with the same name as the function being called, treat this as an
    # object method call and qualify the span name with the object's
    # class. This works for instance and class methods and avoids using
    # the function object's class (which is always True).
    if f_args:
        first = f_args[0]
        try:
            if hasattr(first, f_func.__name__):
                attr = getattr(first, f_func.__name__)
                if inspect.ismethod(attr) or inspect.isfunction(attr) or callable(attr):
                    cls = first.__class__
                    name = f"{cls.__module__}.{cls.__name__}.{f_func.__name__}"
                    object_id = getattr(first, 'id', None)
        except Exception:
            # Fall back to module-level name below
            name = None

    if not name:
        name = f"{f_func.__module__}.{f_func.__name__}"

    attributes: dict[str, Any] = {}
    if object_id:
        attributes['obj'] = f"{object_id}"
    if f_args:
        attributes['args'] = [normalize_attribute(arg, trace_details_val) for arg in f_args]
    if f_kwargs:
        attributes['kwargs'] = normalize_attribute(f_kwargs, trace_details_val)
    return otel_tracer.start_as_current_span(name, attributes=attributes)

def trace(*decorator_args: Any, **decorator_kwargs: Any) -> Callable:
    level = decorator_kwargs.get('level', 1)
    filter = decorator_kwargs.get('filter')
    def trace2_wrapper(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            trace_level_cv, trace_details_cv = _get_context_vars()
            trace_level_val = trace_level_cv.get()
            trace_details_val = trace_details_cv.get()
            ret = None
            with trace_context_factory(level, filter, func, args, kwargs, trace_level_val, trace_details_val) as trace_ctx:
                ret = func(*args, **kwargs)
                # Skip normalizing (stringifying) the return value entirely when
                # this call wasn't actually traced - set_attribute on the
                # pass-through context is a no-op, but normalize_attribute's
                # work (str() on arbitrary objects) isn't, and there's no point
                # paying for it just to discard the result.
                if ret is not None and trace_ctx is not _PASS_THRU:
                    trace_ctx.set_attribute('return', normalize_attribute(ret, trace_details_val))
            return ret
        return wrapper
    if decorator_args and callable(decorator_args[0]):
        # Decorator called without arguments
        return trace2_wrapper(decorator_args[0])
    else:
        # Decorator called with arguments
        return trace2_wrapper
