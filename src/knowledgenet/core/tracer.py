import functools
from time import time
import inspect
from contextlib import AbstractContextManager
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

def trace_context_factory(level: int, filter: Callable[[tuple, dict], bool] | None, f_func: Callable, f_args: tuple, f_kwargs: dict) -> AbstractContextManager[Any]:
    from knowledgenet.service import trace_level, trace_details
    trace_details_val = trace_details.get()
    trace_level_val = trace_level.get()
    filter_pass = filter(f_args, f_kwargs) if filter else True
    to_trace = trace_level_val >= level and filter_pass
    if not to_trace:
        return PassThruTraceContext()

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
            #print(f'{func.__name__}({args}, {kwargs}), level={level}, filter={filter}')
            from knowledgenet.service import trace_details
            trace_details_val = trace_details.get()
            ret = None
            with trace_context_factory(level, filter, func, args, kwargs) as trace_ctx:
                ret = func(*args, **kwargs)
                if ret is not None:
                    trace_ctx.set_attribute('return', normalize_attribute(ret, trace_details_val))
            return ret
        return wrapper
    if decorator_args and callable(decorator_args[0]):
        # Decorator called without arguments
        #print('without', decorator_args, decorator_kwargs)
        return trace2_wrapper(decorator_args[0])
    else:
        # Decorator called with arguments
        #print('with', decorator_args, decorator_kwargs)
        return trace2_wrapper