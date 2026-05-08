import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services import learning as learning_module
from app.services.learning import learning_service


class LearningEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls._original_log_path = learning_module.LEARNING_LOG_PATH
        learning_module.LEARNING_LOG_PATH = Path(cls._temp_dir.name) / "learning.log"
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        learning_service.shutdown()
        learning_module.LEARNING_LOG_PATH = cls._original_log_path
        cls._temp_dir.cleanup()

    def test_best_practices_contains_cpu_section(self):
        response = self.client.get("/api/v1/learning/best-practices")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        titles = [section["title"] for section in data["sections"]]
        self.assertIn("4. CPU 密集任务", titles)

    def test_async_io_demo(self):
        response = self.client.get("/api/v1/learning/async-io-demo", params={"delay_ms": 20})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["pattern"], "async-io")
        self.assertEqual(data["delay_ms"], 20)
        self.assertGreaterEqual(data["elapsed_ms"], 10)

    def test_threadpool_demo(self):
        response = self.client.get("/api/v1/learning/threadpool-demo", params={"delay_ms": 20})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["pattern"], "threadpool-offload")
        self.assertTrue(data["worker_thread"])

    def test_background_task_demo(self):
        note = "background-task-test"
        response = self.client.post("/api/v1/learning/background-task-demo", json={"note": note})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["status"], "queued")
        log_path = Path(data["log_path"])

        for _ in range(20):
            if log_path.exists():
                break
            time.sleep(0.05)

        self.assertTrue(log_path.exists())
        self.assertIn(note, log_path.read_text(encoding="utf-8"))

    def test_bounded_concurrency_demo(self):
        payload = {"task_delays_ms": [20, 20, 40], "max_concurrency": 2}
        response = self.client.post("/api/v1/learning/bounded-concurrency-demo", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["pattern"], "bounded-concurrency")
        self.assertEqual(data["total_tasks"], 3)
        self.assertEqual(len(data["results"]), 3)

    def test_cpu_task_demo_submit_and_poll(self):
        response = self.client.post("/api/v1/learning/cpu-task-demo", json={"iterations": 1500})
        self.assertEqual(response.status_code, 202)
        data = response.json()

        self.assertEqual(data["pattern"], "cpu-task-queue")
        self.assertEqual(data["status"], "queued")
        task_id = data["task_id"]

        final_data = None
        for _ in range(50):
            poll_response = self.client.get(f"/api/v1/learning/cpu-task-demo/{task_id}")
            self.assertEqual(poll_response.status_code, 200)
            final_data = poll_response.json()
            if final_data["status"] in {"completed", "failed"}:
                break
            time.sleep(0.05)

        self.assertIsNotNone(final_data)
        self.assertEqual(final_data["status"], "completed")
        self.assertEqual(final_data["iterations"], 1500)
        self.assertIsNotNone(final_data["result"])
        self.assertGreater(final_data["result"]["prime_count"], 0)

    def test_cpu_task_demo_not_found(self):
        response = self.client.get("/api/v1/learning/cpu-task-demo/not-exists")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
