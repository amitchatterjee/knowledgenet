from typing import List

def _parse_part(part: str) -> tuple[str, int|None]:
    if '[' in part and part.endswith(']'):
        name, idx = part[:-1].split('[')
        return name, int(idx)
    return part, None

def shape(properties: dict[str,str]) -> dict[str, object|List]:
    result = {}
    for key, value in properties.items():
        parts = key.split('.')
        current = result
        for part in parts[:-1]:
            name, idx = _parse_part(part)
            if idx is not None:
                current = current.setdefault(name, [])
                while len(current) <= idx:
                    current.append({})
                current = current[idx]
            else:
                current = current.setdefault(name, {})
        
        name, idx = _parse_part(parts[-1])
        if idx is not None:
            current.setdefault(name, [])
            while len(current[name]) <= idx:
                current[name].append(None)
            current[name][idx] = value
        else:
            current[name] = value
            
    return result
