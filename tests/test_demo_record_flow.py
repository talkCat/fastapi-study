import unittest

from fastapi.testclient import TestClient

from app.main import app


class DemoRecordFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        init_response = cls.client.post("/api/v1/demo-records/init-table")
        cls.init_status = init_response.status_code
        cls.init_payload = init_response.json()

    def test_demo_record_crud_flow(self):
        self.assertEqual(self.init_status, 200)
        self.assertEqual(self.init_payload["code"], 200)

        create_response = self.client.post(
            "/api/v1/demo-records/",
            json={
                "title": "java-to-python-demo",
                "content": "这是一个从 controller 到 service 到 dao 的学习记录",
                "owner": "dev",
                "status": "draft"
            }
        )
        self.assertIn(create_response.status_code, {201, 400})
        if create_response.status_code == 400:
            list_response = self.client.get("/api/v1/demo-records/")
            self.assertEqual(list_response.status_code, 200)
            records = list_response.json()["data"]["items"]
            record = next(item for item in records if item["title"] == "java-to-python-demo")
        else:
            payload = create_response.json()
            self.assertEqual(payload["code"], 201)
            record = payload["data"]

        record_id = record["id"]

        get_response = self.client.get(f"/api/v1/demo-records/{record_id}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["data"]["id"], record_id)

        update_response = self.client.put(
            f"/api/v1/demo-records/{record_id}",
            json={"status": "published"}
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["status"], "published")

        delete_response = self.client.delete(f"/api/v1/demo-records/{record_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["code"], 200)

        get_deleted_response = self.client.get(f"/api/v1/demo-records/{record_id}")
        self.assertEqual(get_deleted_response.status_code, 404)
        self.assertEqual(get_deleted_response.json()["code"], 404)


if __name__ == "__main__":
    unittest.main()
