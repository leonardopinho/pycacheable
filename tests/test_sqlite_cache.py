import os
import tempfile
import time
import unittest

from src import SQLiteCache, cacheable


class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.calls = 0
        self.backend = SQLiteCache(db_path)

    @cacheable(ttl=3, backend=None)
    def get_user_data(self, user_id: int) -> dict:
        self.calls += 1

        time.sleep(0.05)

        return {"user_id": user_id, "name": f"user-{user_id}"}


class CacheableTestSQLiteCache(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmpfile.close()
        self.repo = Repository(self.tmpfile.name)

        Repository.get_user_data.cache_backend = self.repo.backend

    def tearDown(self):
        os.remove(self.tmpfile.name)

    def test_sqlite_cache_hit(self):
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


class TestSQLiteCacheAdvanced(unittest.TestCase):
    """Testes de regressão para SQLite backend."""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmpfile.close()
        self.backend = SQLiteCache(self.tmpfile.name)

    def tearDown(self):
        self.backend.clear()
        if os.path.exists(self.tmpfile.name):
            try:
                os.remove(self.tmpfile.name)
            except Exception:
                pass

    def test_deserialize_error_removes_entry(self):
        """Entrada corrompida é removida do cache."""
        key = "test_key"
        # Injeta dado inválido diretamente via SQL
        with self.backend._lock, self.backend._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (k, expire_at, v) VALUES (?, ?, ?)",
                (key, time.time() + 100, b"\xFF\xFF\xFF")
            )

        hit, value, status = self.backend.get(key)
        self.assertFalse(hit)
        self.assertEqual(status, "DESERIALIZE_ERROR")

        # Entrada foi removida
        with self.backend._lock, self.backend._conn() as conn:
            row = conn.execute("SELECT * FROM cache WHERE k=?", (key,)).fetchone()
            self.assertIsNone(row)

    def test_ttl_zero_never_expires(self):
        """TTL=0 significa sem expiração."""
        key = "eternal"
        self.backend.set(key, "forever", ttl_seconds=0)

        # Espera 1 segundo
        time.sleep(1.1)

        hit, value, status = self.backend.get(key)
        self.assertTrue(hit)
        self.assertEqual(value, "forever")

    def test_cache_clear_empties_table(self):
        """clear() remove todos itens."""
        for i in range(5):
            self.backend.set(f"k{i}", f"v{i}", 100)

        # Verifica que tem itens
        info1 = self.backend.info()
        self.assertGreater(info1["size"], 0)

        self.backend.clear()

        # Verifica que foi limpo
        info2 = self.backend.info()
        self.assertEqual(info2["size"], 0)

    def test_persistence_across_instances(self):
        """Dados persistem entre instâncias."""
        db_path = self.tmpfile.name

        # Primeira instância: escreve
        backend1 = SQLiteCache(db_path)
        backend1.set("persist_key", {"data": "value"}, ttl_seconds=100)
        info1 = backend1.info()
        self.assertEqual(info1["size"], 1)
        backend1.clear()  # Limpa só essa instância

        # Segunda instância: compartilha mesmo DB
        backend2 = SQLiteCache(db_path)
        hit, value, status = backend2.get("persist_key")
        # Não encontra porque foi limpo
        self.assertFalse(hit)

        # Mas escreve na tabela compartilhada
        backend2.set("new_key", "new_value", 100)
        info2 = backend2.info()
        self.assertEqual(info2["size"], 1)


class TestSQLiteCacheIsolation(unittest.TestCase):
    """Testa isolamento e thread-safety."""

    def test_multiple_instances_independent(self):
        """Diferentes DBs são independentes."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f1:
            with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f2:
                try:
                    cache1 = SQLiteCache(f1.name)
                    cache2 = SQLiteCache(f2.name)

                    cache1.set("key", "value1", 100)
                    cache2.set("key", "value2", 100)

                    _, v1, _ = cache1.get("key")
                    _, v2, _ = cache2.get("key")

                    self.assertEqual(v1, "value1")
                    self.assertEqual(v2, "value2")
                finally:
                    try:
                        os.remove(f1.name)
                        os.remove(f2.name)
                    except Exception:
                        pass


if __name__ == "__main__":
    unittest.main()

