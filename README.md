# Aurelia Estates Backend

## Requirements

- Python 3.9 or later

The backend uses Python's standard library and SQLite; no Python packages are needed. On Windows, verify the interpreter is installed and on PATH with `python --version` before starting. If Windows offers to open the Microsoft Store, install Python 3.9+ and enable its PATH option.

## Start

From this project folder, run:

```powershell
python server.py
```

Then open `http://127.0.0.1:8000`. Set `PORT` to use a different port. For a deployment that must accept traffic from other machines, set `HOST=0.0.0.0` and put the app behind an HTTPS reverse proxy. Stop the server with `Ctrl+C`.

The first start creates `aurelia.db` in this folder and seeds the featured properties. Submitted inquiries persist in the same SQLite database.

## API

- `GET /api/properties` returns the featured property records.
- `GET /api/health` returns the service and database health status.
- `POST /api/inquiries` accepts JSON containing `name`, `email`, `phone`, `interest`, and `message`; valid submissions are stored and return HTTP `201`.

There are no admin or inquiry-list endpoints in this initial backend.

## Tests

Run the API and SQLite tests with:

```powershell
python -m unittest -v test_server
```