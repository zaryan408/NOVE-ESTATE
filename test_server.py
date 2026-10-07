import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import server


class BackendApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_directory = tempfile.TemporaryDirectory()
        cls.original_database_path = server.DATABASE_PATH
        server.DATABASE_PATH = Path(cls.database_directory.name) / "test.sqlite"
        server.initialize_database()
        cls.http_server = server.ThreadingHTTPServer(
            ("127.0.0.1", 0), server.AureliaHandler
        )
        cls.server_thread = threading.Thread(
            target=cls.http_server.serve_forever, daemon=True
        )
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.http_server.server_port}"

    def setUp(self):
        with sqlite3.connect(server.DATABASE_PATH) as connection:
            connection.execute("DELETE FROM inquiries")

    @classmethod
    def tearDownClass(cls):
        cls.http_server.shutdown()
        cls.http_server.server_close()
        cls.server_thread.join()
        server.DATABASE_PATH = cls.original_database_path
        cls.database_directory.cleanup()

    def request_json(self, path, payload=None, content_type="application/json"):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": content_type},
            method="GET" if payload is None else "POST",
        )
        try:
            response = urlopen(request)
        except HTTPError as error:
            response = error
        with response:
            raw_body = response.read()
            parsed_body = json.loads(raw_body) if raw_body else None
            return response.status, parsed_body, response.headers

    def valid_inquiry(self):
        return {
            "name": "Ayesha Khan",
            "email": "ayesha@example.com",
            "phone": "+92 300 1234567",
            "interest": "Luxury Villa",
            "message": "I would like to arrange a viewing.",
        }

    def test_health_and_seeded_properties(self):
        health_status, health, _ = self.request_json("/api/health")
        property_status, payload, _ = self.request_json("/api/properties")

        self.assertEqual(health_status, 200)
        self.assertEqual(health["status"], "ok")
        self.assertEqual(property_status, 200)
        self.assertEqual(len(payload["properties"]), 3)

    def test_inquiry_is_validated_and_persisted(self):
        status, payload, headers = self.request_json(
            "/api/inquiries", self.valid_inquiry()
        )

        self.assertEqual(status, 201)
        self.assertEqual(payload["name"], "Ayesha Khan")
        self.assertEqual(headers["Cache-Control"], "no-store")
        with sqlite3.connect(server.DATABASE_PATH) as connection:
            stored = connection.execute(
                "SELECT name, email, phone, interest, message, created_at FROM inquiries"
            ).fetchone()
        self.assertEqual(stored[:5], tuple(self.valid_inquiry().values()))
        self.assertTrue(stored[5])

    def test_invalid_inquiry_is_rejected_without_saving(self):
        invalid = self.valid_inquiry()
        invalid["email"] = "not-an-email"
        status, payload, _ = self.request_json("/api/inquiries", invalid)

        self.assertEqual(status, 400)
        self.assertIn("email", payload["error"].lower())
        with sqlite3.connect(server.DATABASE_PATH) as connection:
            count = connection.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0]
        self.assertEqual(count, 0)

    def test_non_json_submission_is_rejected(self):
        status, payload, _ = self.request_json(
            "/api/inquiries", self.valid_inquiry(), "text/plain"
        )

        self.assertEqual(status, 415)
        self.assertIn("application/json", payload["error"])

    def test_malformed_and_oversized_payloads_are_rejected(self):
        request = Request(
            self.base_url + "/api/inquiries",
            data=b"{invalid",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as malformed:
            urlopen(request)
        self.assertEqual(malformed.exception.code, 400)

        request = Request(
            self.base_url + "/api/inquiries",
            data=b" " * (server.MAX_REQUEST_BYTES + 1),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as oversized:
            urlopen(request)
        self.assertEqual(oversized.exception.code, 400)

    def test_unsupported_method_returns_allowed_methods(self):
        request = Request(
            self.base_url + "/api/properties", data=b"{}", method="PUT"
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)

        self.assertEqual(raised.exception.code, 405)
        self.assertEqual(raised.exception.headers["Allow"], "GET, HEAD")

    def test_database_and_backend_files_are_not_public(self):
        for filename in ("aurelia.db", "server.py", "README.md"):
            with self.subTest(filename=filename):
                status, _, _ = self.request_json("/" + filename)
                self.assertEqual(status, 404)

        request = Request(self.base_url + "/aurelia.db", method="HEAD")
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 404)


if __name__ == "__main__":
    unittest.main()