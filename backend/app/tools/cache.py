import time
from functools import wraps

from app import config

_store: dict = {}


def cached(fn):
    """10-minute TTL cache keyed by function and arguments. Errors are not cached."""

    @wraps(fn)
    def wrapper(*args):
        key = (fn.__name__, args)
        hit = _store.get(key)
        if hit and time.time() - hit[0] < config.CACHE_TTL:
            return hit[1]
        value = fn(*args)
        if "error" not in value:
            _store[key] = (time.time(), value)
        return value

    return wrapper
