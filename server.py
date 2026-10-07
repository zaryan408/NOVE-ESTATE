import json
import os
import re
import sqlite3
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "aurelia.db"
MAX_REQUEST_BYTES = 16_384
INTERESTS = {
    "Luxury Villa",
    "Penthouse",
    "Apartment",
    "House",
    "Commercial Property",
}
SEED_PROPERTIES = [
    (
        "The Aurelia Residence",
        "Beverly Hills, California",
        1850000,
        "FOR SALE",
        4,
        3,
        3850,
        "https://images.unsplash.com/photo-1600607688969-a5bfcd646154?auto=format&fit=crop&w=1400&q=90",
    ),
    (
        "Ocean View Villa",
        "Miami, Florida",
        2400000,
        "FEATURED",
        5,
        4,
        4620,
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1400&q=90",
    ),
    (
        "Manhattan Penthouse",
        "New York, USA",
        3150000,
        "FOR SALE",
        3,
        3,
        3200,
        "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1400&q=90",
    ),
]


def connect_database():
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def database_connection():
    connection = connect_database()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with database_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                interest TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                location TEXT NOT NULL,
                price INTEGER NOT NULL,
                status TEXT NOT NULL,
                beds INTEGER NOT NULL,
                baths INTEGER NOT NULL,
                area_sqft INTEGER NOT NULL,
                image_url TEXT NOT NULL
            );
            """
        )
        property_count = connection.execute(
            "SELECT COUNT(*) FROM properties"
        ).fetchone()[0]
        if property_count == 0:
            connection.executemany(
                """
                INSERT INTO properties
                    (title, location, price, status, beds, baths, area_sqft, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                SEED_PROPERTIES,
            )


def validate_inquiry(payload):
    if not isinstance(payload, dict):
        raise ValueError("Please submit a valid inquiry.")

    limits = {"name": 120, "email": 254, "phone": 40, "interest": 80, "message": 5000}
    inquiry = {}
    for field, max_length in limits.items():
        value = payload.get(field)
        if not isinstance(value, str):
            raise ValueError(f"{field.title()} is required.")
        value = value.strip()
        if not value:
            raise ValueError(f"{field.title()} is required.")
        if len(value) > max_length:
            raise ValueError(f"{field.title()} is too long.")
        inquiry[field] = value

    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", inquiry["email"]):
        raise ValueError("Please enter a valid email address.")
    if len(re.sub(r"\D", "", inquiry["phone"])) < 7:
        raise ValueError("Please enter a valid phone number.")
    if inquiry["interest"] not in INTERESTS:
        raise ValueError("Please select a valid property interest.")
    return inquiry


class AureliaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            try:
                with database_connection() as connection:
                    connection.execute("SELECT 1")
            except sqlite3.Error:
                self.send_json(503, {"error": "Service temporarily unavailable."})
                return
            self.send_json(200, {"status": "ok"})
            return
        if path == "/api/properties":
            try:
                with database_connection() as connection:
                    properties = [
                        dict(row)
                        for row in connection.execute(
                            """
                            SELECT id, title, location, price, status, beds, baths,
                                   area_sqft, image_url
                            FROM properties ORDER BY id
                            """
                        )
                    ]
            except sqlite3.Error:
                self.send_json(503, {"error": "Properties are temporarily unavailable."})
                return
            self.send_json(200, {"properties": properties})
            return
        if path not in {"/", "/index.html", "/script.js", "/style.css"}:
            self.send_json(404, {"error": "Not found."})
            return
        super().do_GET()

    def do_HEAD(self):
        if urlsplit(self.path).path not in {"/", "/index.html", "/script.js", "/style.css"}:
            self.send_response(404)
            self.end_headers()
            return
        super().do_HEAD()

    def do_POST(self):
        path = urlsplit(self.path).path
        if path in {"/api/properties", "/api/health"}:
            self.send_response(405)
            self.send_header("Allow", "GET, HEAD")
            self.end_headers()
            return
        if path != "/api/inquiries":
            self.send_json(404, {"error": "API route not found."})
            return

        if not self.headers.get("Content-Type", "").startswith("application/json"):
            self.send_json(415, {"error": "Content-Type must be application/json."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length < 1 or content_length > MAX_REQUEST_BYTES:
                raise ValueError("Inquiry payload is missing or too large.")
            payload = json.loads(self.rfile.read(content_length))
            inquiry = validate_inquiry(payload)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self.send_json(400, {"error": str(error)})
            return

        try:
            with database_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO inquiries (name, email, phone, interest, message)
                    VALUES (:name, :email, :phone, :interest, :message)
                    """,
                    inquiry,
                )
                inquiry_id = cursor.lastrowid
        except sqlite3.Error:
            self.send_json(503, {"error": "Your inquiry could not be saved. Please try again."})
            return

        self.send_json(201, {"id": inquiry_id, "name": inquiry["name"]})

    def reject_method(self):
        self.send_response(405)
        path = urlsplit(self.path).path
        allowed = "POST" if path == "/api/inquiries" else "GET, HEAD"
        self.send_header("Allow", allowed)
        self.end_headers()

    do_PUT = reject_method
    do_PATCH = reject_method
    do_DELETE = reject_method
    do_OPTIONS = reject_method

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        super().end_headers()

    def send_json(self, status, payload):
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response)


if __name__ == "__main__":
    initialize_database()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), AureliaHandler)
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    print(f"Aurelia Estates is running at http://{display_host}:{port}")
    print(f"SQLite database: {DATABASE_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()