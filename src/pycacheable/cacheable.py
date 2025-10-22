import functools
from typing import Any, Callable, Dict, Optional, Tuple

from src.pycacheable.backend_sqlite import SQLiteCache
from src.pycacheable.hashing import _build_key_from_call


def cacheable(
        ttl: Optional[int] = 300,
        backend: Optional[object] = None,
        *,
        include_self: bool = False,
        key_fn: Optional[Callable[[Callable, Tuple[Any, ...], Dict[str, Any]], str]] = None,
        logger: Optional[Callable[[str], None]] = None,
        backend_factory: Optional[Callable[..., object]] = None,
):
    default_backend = backend or SQLiteCache(path="./.cache/db.sqlite3")

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            be = getattr(wrapper, "cache_backend", None)
            if be is None and backend_factory is not None:
                try:
                    be = backend_factory(*args, **kwargs)
                except TypeError:
                    be = backend_factory(args[0]) if args else None
            if be is None:
                be = default_backend

            key = (key_fn(func, args, kwargs)
                   if key_fn else _build_key_from_call(func, args, kwargs, include_self))

            hit, value, status = be.get(key)
            if hit:
                if logger: logger(f"[CACHE {status}] {func.__qualname__} {key[:10]}…")
                return value

            if logger: logger(f"[CACHE {status}] {func.__qualname__} {key[:10]}… -> calling")
            result = func(*args, **kwargs)
            try:
                be.set(key, result, ttl)
                if logger: logger(f"[CACHE SET] {func.__qualname__} {key[:10]}… ttl={ttl}")
            except Exception as e:
                if logger: logger(f"[CACHE ERROR SET] {func.__qualname__}: {e}")
            return result

        wrapper.cache_backend = default_backend
        wrapper.cache_clear = lambda: wrapper.cache_backend.clear()
        wrapper.cache_info = lambda: wrapper.cache_backend.info()
        return wrapper

    return decorator
