"""Testes para estratégias de serialização."""
import unittest
from datetime import datetime

from src.pycacheable.serializers import SafeSerializer


# Classe module-level para pickling
class PickleableClass:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, PickleableClass) and self.value == other.value


class TestSafeSerializer(unittest.TestCase):
    """Valida SafeSerializer com JSON-first + pickle fallback."""

    def setUp(self):
        self.ser = SafeSerializer()

    def test_json_primitive_types(self):
        """JSON handles primitives."""
        for obj in [42, "hello", 3.14, True, None, [1, 2, 3], {"a": 1}]:
            with self.subTest(obj=obj):
                data = self.ser.dumps(obj)
                self.assertTrue(
                    data.startswith(b"\x00"),
                    f"Should use JSON prefix for {obj}"
                )
                restored = self.ser.loads(data)
                self.assertEqual(restored, obj)

    def test_pickle_complex_objects(self):
        """Pickle handles datetime, custom objects."""
        obj = datetime.now()
        data = self.ser.dumps(obj)
        self.assertTrue(
            data.startswith(b"\x01"),
            "Should use pickle prefix for datetime"
        )
        restored = self.ser.loads(data)
        self.assertEqual(restored, obj)

    def test_json_list_of_dicts(self):
        """Lists and dicts use JSON."""
        obj = [{"id": 1}, {"id": 2}]
        data = self.ser.dumps(obj)
        self.assertTrue(data.startswith(b"\x00"))
        self.assertEqual(self.ser.loads(data), obj)

    def test_pickle_fallback_custom_object(self):
        """Custom objects use pickle fallback."""
        obj = PickleableClass(42)
        data = self.ser.dumps(obj)
        self.assertTrue(data.startswith(b"\x01"))
        restored = self.ser.loads(data)
        self.assertEqual(restored, obj)

    def test_empty_data_raises(self):
        """Empty data raises ValueError."""
        with self.assertRaises(ValueError):
            self.ser.loads(b"")

    def test_invalid_prefix_raises(self):
        """Unknown prefix raises ValueError."""
        with self.assertRaises(ValueError):
            self.ser.loads(b"\x99unknown")

    def test_nested_structures(self):
        """Nested JSON structures work correctly."""
        obj = {
            "users": [
                {"id": 1, "name": "Alice", "tags": ["admin", "user"]},
                {"id": 2, "name": "Bob", "tags": ["user"]}
            ],
            "count": 2
        }
        data = self.ser.dumps(obj)
        restored = self.ser.loads(data)
        self.assertEqual(restored, obj)

    def test_unicode_strings(self):
        """Unicode strings serialize correctly."""
        obj = {"emoji": "🚀", "chinese": "你好", "arabic": "مرحبا"}
        data = self.ser.dumps(obj)
        restored = self.ser.loads(data)
        self.assertEqual(restored, obj)


class TestSerializerIntegration(unittest.TestCase):
    """Valida serializer com backends."""

    def test_safe_roundtrip_dict(self):
        ser = SafeSerializer()
        original = {"user_id": 42, "name": "Alice"}
        data = ser.dumps(original)
        restored = ser.loads(data)
        self.assertEqual(restored, original)

    def test_safe_roundtrip_list(self):
        ser = SafeSerializer()
        original = [1, 2, 3, "test", {"key": "value"}]
        data = ser.dumps(original)
        restored = ser.loads(data)
        self.assertEqual(restored, original)


if __name__ == "__main__":
    unittest.main()
