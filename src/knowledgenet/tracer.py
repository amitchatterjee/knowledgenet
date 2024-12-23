from time import time
import traceback

def timestamp():
    return int(round(time() * 1000))

def trace(filter=None):
    def decorator(func):    
        def wrapper(*args, **kwargs):
            from service import trace_buffer
            buffer = trace_buffer.get()
            
            filter_pass = filter(args, kwargs) if filter else True
            if buffer is not None and filter_pass:            
                class_name = f"{args[0].__class__.__module__}.{args[0].__class__.__name__}" if args else 'Unknown'
                object_id = getattr(args[0], 'id', 'unknown')
                func_name = func.__name__
                trace = {'func': f"{class_name}.{func_name}",
                    'obj': f"{object_id}",
                    'args': [f"{arg}" for arg in args],
                    'kwargs': kwargs,
                    'start': timestamp(),
                    'children': []
                }
                trace_buffer.set(trace['children'])
            ret = None
            exception_trace = None
            try:
                ret = func(*args, **kwargs)
            except Exception as e:
                exception_trace = traceback.format_exc()
                raise e
            finally:
                if buffer is not None and filter_pass:
                    trace['end'] = timestamp()
                    trace['ret'] = f"{ret}"
                    if exception_trace:
                        trace['exc'] = exception_trace
                    buffer.append(trace)
                    trace_buffer.set(buffer)
            return ret
        wrapper.__wrapped__ = True
        return wrapper
    decorator.__wrapped__ = True
    return decorator
