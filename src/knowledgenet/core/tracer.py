from time import time
import traceback

from opentelemetry import trace as otel_trace

class NoneTraceContext:
    def __init__(self):
        ...
    def __enter__(self):
        return self
    def set_attribute(self, key, val):
        ...
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

class StreamTraceContext:
    def __init__(self, trace_buffer, f_func, f_args, f_kwargs):
        self.trace_buffer = trace_buffer
        self.f_func = f_func
        self.f_args = f_args
        self.f_kwargs = f_kwargs
        self.buffer = trace_buffer.get()
        self.attributes = {}
    
    def __enter__(self):
        class_name = f"{self.f_args[0].__class__.__module__}.{self.f_args[0].__class__.__name__}" if self.f_args else 'Unknown'
        object_id = getattr(self.f_args[0], 'id', 'unknown')
        func_name = self.f_func.__name__
        self.trace = {'obj': f"{object_id}",
            'func': f"{class_name}.{func_name}",
            'args': [f"{arg}" for arg in self.f_args],
            'kwargs': self.f_kwargs,
            'start': timestamp(),
            'calls': []
        }
        self.trace_buffer.set(self.trace['calls'])
        return self
    
    def set_attribute(self, key, val):
        self.attributes[key] = str(val)

    def __exit__(self, exc_type, exc_val, exc_tb):
        exception_trace = None
        if exc_type is not None:
            # Exception occured
            exception_trace = traceback.format_exc("".join(traceback.format_exception(exc_type, exc_val, exc_tb)))

        self.trace['end'] = timestamp()
        # add collected attributes into the trace (safely convert values to strings if needed)
        
        self.trace.update(self.attributes)

        if exception_trace:
            self.trace['exc'] = exception_trace
        self.buffer.append(self.trace)
        self.trace_buffer.set(self.buffer)
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

def trace_context_factory(to_trace, trace_method, trace_buffer, f_func, f_args, f_kwargs):
    if not to_trace:
        return NoneTraceContext()
    
    method = trace_method.get()

    if method == 'legacy':
        return StreamTraceContext(trace_buffer, f_func, f_args, f_kwargs)
    
    if method == 'otel':
        class_name = f"{f_args[0].__class__.__module__}.{f_args[0].__class__.__name__}" if f_args else 'Unknown'
        func_name = f_func.__name__
        object_id = getattr(f_args[0], 'id', 'unknown')
        attributes = {'obj': f"{object_id}",
            'args': [normalize_attribute(arg) for arg in f_args],
            'kwargs': normalize_attribute(f_kwargs)
        }
        return otel_tracer.start_as_current_span(f"{class_name}.{func_name}", attributes=attributes)
    raise Exception('NYI')

def trace(filter=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            from knowledgenet.service import trace_method, trace_buffer
            method = trace_method.get()
            
            filter_pass = filter(args, kwargs) if filter else True
            to_trace = method is not None and filter_pass
            ret = None
            with trace_context_factory(to_trace, trace_method, trace_buffer, func, args, kwargs) as trace_ctx:
                ret = func(*args, **kwargs)
                if ret is not None:
                    trace_ctx.set_attribute('ret', normalize_attribute(ret))
            return ret
        wrapper.__wrapped__ = True
        return wrapper
    decorator.__wrapped__ = True
    return decorator
