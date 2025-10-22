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
