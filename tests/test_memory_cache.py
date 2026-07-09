import time
import unittest

from src import cacheable, InMemoryCache


class Repository:
    def __init__(self):
        self.calls = 0
        self.backend = InMemoryCache(max_entries=1024)

    @cacheable(ttl=3, backend=None)
    def get_user_data(self, user_id: int) -> dict:
        self.calls += 1

        time.sleep(0.05)

        return {"user_id": user_id, "name": f"user-{user_id}"}


class CacheableTestMemoryCache(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        Repository.get_user_data.cache_backend = self.repo.backend

    def test_memory_cache_hit(self):
        u1 = self.repo.get_user_data(1)
        self.assertEqual(u1["name"], "user-1")
        self.assertEqual(self.repo.calls, 1)

        u2 = self.repo.get_user_data(1)
        self.assertEqual(u2["name"], "user-1")
        self.assertEqual(self.repo.calls, 1)

        info = self.repo.backend.info()
        self.assertIn("size", info)
        self.assertGreaterEqual(info["size"], 1)

    def test_sqlite_cache_expire(self):
        _ = self.repo.get_user_data(2)
        self.assertEqual(self.repo.calls, 1)

        _ = self.repo.get_user_data(2)
        self.assertEqual(self.repo.calls, 1)

        time.sleep(3.5)

        _ = self.repo.get_user_data(2)
        self.assertEqual(self.repo.calls, 2, "Após TTL, método deve ser executado novamente")


class TestMemoryCacheAdvanced(unittest.TestCase):
    """Testes de regressão para isolamento, serialização e edge cases."""

    def setUp(self):
        self.backend = InMemoryCache(max_entries=10)

    def test_deserialize_error_removes_entry(self):
        """Entrada corrompida é removida do cache."""
        key = "test_key"
        # Injeta dado inválido
        self.backend._store[key] = (time.time() + 100, b"\xFF\xFF\xFF")

        hit, value, status = self.backend.get(key)
        self.assertFalse(hit)
        self.assertEqual(status, "DESERIALIZE_ERROR")
        # Entrada foi removida
        self.assertNotIn(key, self.backend._store)

    def test_ttl_zero_never_expires(self):
        """TTL=0 significa sem expiração."""
        key = "eternal"
        self.backend.set(key, "forever", ttl_seconds=0)

        # Espera 1 segundo
        time.sleep(1.1)

        hit, value, status = self.backend.get(key)
        self.assertTrue(hit)
        self.assertEqual(value, "forever")

    def test_lru_eviction_order(self):
        """Itens antigos são evicados em ordem LRU."""
        for i in range(15):  # max_entries=10
            self.backend.set(f"key_{i}", f"value_{i}", ttl_seconds=100)

        # Últimas 10 chaves devem estar presentes
        for i in range(5, 15):
            hit, _, _ = self.backend.get(f"key_{i}")
            self.assertTrue(hit, f"key_{i} should still be cached")

        # Primeiras 5 devem ter sido evicadas
        for i in range(5):
            hit, _, _ = self.backend.get(f"key_{i}")
            self.assertFalse(hit, f"key_{i} should have been evicted")

    def test_cache_clear_empties_store(self):
        """clear() remove todos itens."""
        for i in range(5):
            self.backend.set(f"k{i}", f"v{i}", 100)

        self.assertGreater(len(self.backend._store), 0)
        self.backend.clear()
        self.assertEqual(len(self.backend._store), 0)


class TestMemoryCacheIsolation(unittest.TestCase):
    """Testa isolamento entre instâncias e métodos."""

    def test_multiple_instances_independent(self):
        """Diferentes instâncias de InMemoryCache são independentes."""
        cache1 = InMemoryCache()
        cache2 = InMemoryCache()

        cache1.set("key", "value1", 100)
        cache2.set("key", "value2", 100)

        _, v1, _ = cache1.get("key")
        _, v2, _ = cache2.get("key")

        self.assertEqual(v1, "value1")
        self.assertEqual(v2, "value2")

    def test_cache_backend_override(self):
        """wrapper.cache_backend override funciona corretamente."""
        repo1 = Repository()
        repo2 = Repository()

        # Ambas usam mesmo backend
        Repository.get_user_data.cache_backend = repo1.backend

        result1 = repo1.get_user_data(99)
        self.assertEqual(repo1.calls, 1)

        result2 = repo2.get_user_data(99)
        # repo2 não executa porque compartilha cache com repo1
        self.assertEqual(repo2.calls, 0)

        self.assertEqual(result1, result2)


if __name__ == "__main__":
    unittest.main()
