"""Estratégias de serialização thread-safe para cache."""
import json
import pickle
from typing import Any


class SafeSerializer:
    """
    Serializer híbrido: tenta JSON (seguro) primeiro, fallback para pickle.

    Prefixos:
    - 0x00: JSON (seguro, sem risco de code execution)
    - 0x01: Pickle (flexível, suporta objetos complexos)

    Exemplo:
        >>> ser = SafeSerializer()
        >>> data = ser.dumps({"user": 42})
        >>> obj = ser.loads(data)
    """

    def dumps(self, obj: Any) -> bytes:
        """Serializa obj para bytes com prefixo de tipo."""
        try:
            # Tenta JSON primeiro
            payload = json.dumps(
                obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            return b"\x00" + payload
        except (TypeError, ValueError):
            # Fallback para pickle
            payload = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
            return b"\x01" + payload

    def loads(self, data: bytes) -> Any:
        """Desserializa bytes baseado no prefixo."""
        if not data or len(data) < 1:
            raise ValueError("Empty serialized data")

        prefix = data[0:1]
        payload = data[1:]

        if prefix == b"\x00":
            return json.loads(payload.decode("utf-8"))
        elif prefix == b"\x01":
            return pickle.loads(payload)
        else:
            prefix_hex = hex(prefix[0]) if prefix else "unknown"
            raise ValueError(f"Unknown serializer prefix: {prefix_hex}")


