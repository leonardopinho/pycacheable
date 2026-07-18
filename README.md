# PyCacheable

A cache decorator for Python methods and functions with in-memory and SQLite backends — automatic serialization with JSON-first + pickle fallback strategy, stable parameter hashing, instance/state support, and pluggable architecture.

---

## Problem

In many Python applications, there are methods that:

- make repeated queries to databases or external APIs;
- receive the same parameters multiple times;
- repeat expensive CPU or I/O work;
- in short: do **the same work more than once**, wasting time and resources.

Without a caching mechanism, each call results in complete re-execution, leading to high latencies, extra load on databases/services, and degraded user experience.

---

## Solution

The library provides:

- A `@cacheable(...)` decorator that wraps functions or methods, generates a **stable key** from parameters (canonical serialization + sha256);
- Backend support:
  - `InMemoryCache`: volatile in-memory cache with LRU + TTL.
  - `SQLiteCache`: persistent disk cache (SQLite) with TTL, ideal for between executions or processes;
- Clear flow logs: HIT / MISS / EXPIRE — allowing you to understand if the cache is working;
- Safe serialization:
  - JSON-first for simple structures (safe, no RCE risk)
  - Pickle fallback for complex objects (flexible)
- Helper methods:
  - `.cache_clear()`, `.cache_info()` on wrapper for inspection/maintenance;

---

## How to use

```python
from src.pycacheable.backend_sqlite import SQLiteCache
from src.pycacheable.backend_memory import InMemoryCache
from src.pycacheable.cacheable import cacheable

mem = InMemoryCache(max_entries=512)
disk = SQLiteCache(path="./.cache/myapp.sqlite")


class Repo:
    @cacheable(ttl=60, backend=mem)
    def get_user(self, user_id: int) -> dict:
        # expensive database query
        return {"user_id": user_id, "name": f"user{user_id}"}

    @cacheable(ttl=300, backend=disk)
    def get_orders(self, user_id: int, status: str = "open") -> list:
        return [{"order_id": 101, "user_id": user_id, "status": status}]


repo = Repo()
u1 = repo.get_user(42)  # MISS → executes query
u2 = repo.get_user(42)  # HIT → returns cache, query not executed
```

---

## Benefits

- Lower latency on repeated calls (hit almost instant).
- Lower load on database/service, less repeated I/O.
- Local persistence (via SQLite) enables cache between restarts/processes.
- Transparent to function users — just apply the decorator.
- Logs and metrics help monitor real impact.
- Safe serialization with JSON-first (no risk of arbitrary code execution).

---

## When to use

- Functions/methods with **deterministic results** (same parameters → same result)  
- Idempotent and repeated queries  
- Expensive CPU or I/O calculations  
- Scenarios where latency matters and repetition should be avoided

---

## Considerations and limits

- Cache avoids re-executions **only if** the method parameters are the same and serializable.
- If the method depends on mutable state outside parameters (e.g., `self.some_state`), you should use `include_self=True` or custom `key_fn`.
- TTL is used for expiration — results may become "stale" if parameters or context change without changing the key.
- Although SQLite backend is persistent, it **does not replace** a distributed cache (e.g., Redis) in multi-process/semi-distributed scenarios.
- Pickle fallback maintains compatibility with complex objects, but use with trusted data.

---

## Benchmarks

See real results measuring MISS vs HIT:

| Backend | MISS (s) | HIT (s) | Speedup | Calls |
|----------|-----------|----------|----------|--------|
| RAW | 0.4410 | — | — | — |
| InMemory | 0.4043 | 0.000043 | ~9,494x | 1 |
| SQLite | 0.4001 | 0.000763 | ~524x | 1 |

Cache reduces execution time from ~0.4 s to ~0.00004 s — a **speedup over 9,000×**.

---

## Next steps

- Support for `async def` functions (awaitable decorator)   
- Redis / LMDB backend for distributed scenarios  
- Metrics and Prometheus integration  

---

## License

MIT License — see the `LICENSE` file for details.
