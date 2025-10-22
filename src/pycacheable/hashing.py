from __future__ import annotations

import datetime as dt
import decimal
import enum
import hashlib
import inspect
import json
import pathlib
import pickle
import uuid
from typing import Any, Mapping, Iterable
from typing import Callable, Dict, Tuple


def _to_canonical(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if isinstance(obj, decimal.Decimal):
        return str(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)

    if isinstance(obj, (dt.datetime, dt.date, dt.time)):
        if isinstance(obj, dt.datetime):
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=dt.timezone.utc)  # padroniza se vier naive
            return obj.astimezone(dt.timezone.utc).isoformat(timespec="microseconds")
        if isinstance(obj, dt.date):
            return obj.isoformat()
        if isinstance(obj, dt.time):
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=dt.timezone.utc)
            return obj.isoformat(timespec="microseconds")

    if isinstance(obj, pathlib.Path):
        return str(obj)
    if isinstance(obj, enum.Enum):
        return obj.value if isinstance(obj.value, (str, int, float, bool)) else obj.name

    if isinstance(obj, set):
        return sorted(_to_canonical(x) for x in obj)
    if isinstance(obj, tuple):
        return ["__tuple__", *(_to_canonical(x) for x in obj)]  # preserva semântica

    if isinstance(obj, Mapping):
        return {str(k): _to_canonical(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}

    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, bytearray)):
        return [_to_canonical(x) for x in obj]

    if isinstance(obj, (bytes, bytearray, memoryview)):
        return {"__bytes__": bytes(obj).hex()}

    try:
        import numpy as np  # type: ignore
        if isinstance(obj, (np.generic,)):  # np.int64, np.float32 etc.
            return obj.item()
        if isinstance(obj, (np.ndarray,)):
            return {"__ndarray__": obj.tolist(), "dtype": str(obj.dtype), "shape": obj.shape}
    except Exception:
        pass

    return {"__type__": type(obj).__name__, "__repr__": repr(obj)}


def _json_canonical_dumps(payload: Any) -> bytes:
    canon = _to_canonical(payload)
    return json.dumps(canon, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o: Any):
        try:
            return {"__type__": type(o).__name__, "__repr__": repr(o)}
        except Exception:
            return super().default(o)


def _json_dumps_canonical(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), cls=EnhancedJSONEncoder).encode("utf-8")


def _stable_hash(payload: Any) -> str:
    try:
        data = _json_canonical_dumps(payload)
    except Exception:
        data = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)

    return hashlib.sha256(data).hexdigest()


def _build_key_from_call(func: Callable, args: Tuple[Any, ...], kwargs: Dict[str, Any], include_self: bool) -> str:
    sig = inspect.signature(func)
    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    items = dict(bound.arguments)

    if not include_self:
        items.pop("self", None)
        items.pop("cls", None)

    key_payload = {
        "fn": f"{func.__module__}.{func.__qualname__}",
        "params": items,
    }

    return _stable_hash(key_payload)
