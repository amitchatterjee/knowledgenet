from time import time
import traceback
import inspect

from opentelemetry import trace as otel_trace

class PassThruTraceContext:
    def __init__(self):
        ...
    def __enter__(self):
        return self
    # The name and signature of this function must match that of otel. DO NOT CHANGE
    def set_attribute(self, key, val):
        ...
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

otel_tracer = otel_trace.get_tracer(__name__)

def timestamp():
    return int(round(time() * 1000))

def normalize_attribute(value):
    # Primitive passthrough
    if isinstance(value, (int, float, str, bool)):
        return value
    # Fallback: stringify
    return str(value)

def trace_context_factory(filter, f_func, f_args, f_kwargs):
    from knowledgenet.service import tracing_option
    method = tracing_option.get()
    filter_pass = filter(f_args, f_kwargs) if filter else True
    to_trace = method is not None and filter_pass
    if not to_trace:
        return PassThruTraceContext()
    
    object_id = None
    name = None
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

    attributes = {}
    if object_id:
        attributes['obj'] = f"{object_id}"
    if f_args:
        attributes['args'] = [normalize_attribute(arg) for arg in f_args]
    if f_kwargs:
        attributes['kwargs'] = normalize_attribute(f_kwargs)
    return otel_tracer.start_as_current_span(name, attributes=attributes)

def trace(filter=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            ret = None
            with trace_context_factory(filter, func, args, kwargs) as trace_ctx:
                ret = func(*args, **kwargs)
                if ret is not None:
                    trace_ctx.set_attribute('ret', normalize_attribute(ret))
            return ret
        wrapper.__wrapped__ = True
        return wrapper
    decorator.__wrapped__ = True
    return decorator
