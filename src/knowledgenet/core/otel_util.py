
import inspect

def span_args(frame, obj):
    frame = inspect.currentframe()
    func_name = frame.f_code.co_name
    attrs = {}
    try:
        arginfo = inspect.getargvalues(frame)
        for name in arginfo.args:
            if name == 'self':
                continue
            val = arginfo.locals.get(name)
            try:
                sval = str(val)
            except Exception:
                sval = repr(val)
            # truncate long values to avoid huge attributes
            #if len(sval) > 200:
            #    sval = sval[:197] + '...'
            #attrs[name] = sval
            attrs[name] = sval
        name = f"{obj.__class__.__module__}.{obj.__class__.__qualname__}.{func_name}"
        return {"name": name, "attributes": attrs}
    finally:
        # avoid reference cycles
        del frame 