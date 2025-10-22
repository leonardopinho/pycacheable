import time
from statistics import median
from dataclasses import dataclass

from src.pycacheable.backend_memory import InMemoryCache
from src.pycacheable.backend_sqlite import SQLiteCache
from src.pycacheable.cacheable import cacheable


def pi_nilakantha(iterations: int) -> float:
    pi = 3.0
    sign = 1.0
    a = 2.0
    for _ in range(iterations):
        term = 4.0 / (a * (a + 1.0) * (a + 2.0))
        pi += sign * term
        sign *= -1.0
        a += 2.0
    return pi


mem = InMemoryCache(max_entries=256)
disk = SQLiteCache("./benchmarks/.cache/bench_pi.sqlite")


class PiService:
    def __init__(self, backend):
        self.calls = 0
        self.backend = backend

    @cacheable(ttl=60, backend_factory=lambda self, *_: self.backend)
    def compute_pi(self, iterations: int) -> float:
        self.calls += 1
        return pi_nilakantha(iterations)


@dataclass
class Stat:
    label: str;
    seconds: float;
    value: float;
    calls: int


def time_one(fn, *args, repeats=1, clear=lambda: None):
    clear()
    # MISS (1ª vez)
    t0 = time.perf_counter()
    v = fn(*args)
    miss = time.perf_counter() - t0
    # HITs (múltiplas vezes)
    hits = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        v = fn(*args)
        hits.append(time.perf_counter() - t0)
    return v, miss, median(hits)


def autotune_iter(target_sec=0.4):
    iter_guess = 300_000
    while True:
        t0 = time.perf_counter()
        _ = pi_nilakantha(iter_guess)
        dt = time.perf_counter() - t0
        if abs(dt - target_sec) / target_sec < 0.25 or iter_guess > 50_000_000:
            return iter_guess
        ratio = target_sec / max(dt, 1e-9)
        iter_guess = int(iter_guess * (0.5 + min(3.0, ratio)))


if __name__ == "__main__":
    ITER = autotune_iter(0.4)

    svc_mem = PiService(mem)
    svc_disk = PiService(disk)

    clear_mem = lambda: svc_mem.compute_pi.cache_clear()
    clear_disk = lambda: svc_disk.compute_pi.cache_clear()

    t0 = time.perf_counter()
    v_raw = pi_nilakantha(ITER)
    raw = time.perf_counter() - t0

    v1, miss_mem, hit_mem = time_one(svc_mem.compute_pi, ITER, repeats=5, clear=clear_mem)

    v2, miss_disk, hit_disk = time_one(svc_disk.compute_pi, ITER, repeats=5, clear=clear_disk)

    print(f"\nITER={ITER:,} | π≈{v_raw:.12f}\n")
    print("Backend     MISS (s)   HIT_med (s)   Speedup(HIT/MISS)   Calls")
    print("----------- ---------- ------------- ------------------- ------")
    print(f"RAW         {raw:10.4f}    —                 —            {'—':>6}")
    print(f"InMemory    {miss_mem:10.4f} {hit_mem:11.6f} {miss_mem / hit_mem:19.1f} {svc_mem.calls:6d}")
    print(f"SQLite      {miss_disk:10.4f} {hit_disk:11.6f} {miss_disk / hit_disk:19.1f} {svc_disk.calls:6d}")
