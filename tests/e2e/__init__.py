"""Neo Agent E2E tests package.

End-to-end tests for the Web GUI / API layer.

These tests exercise the FastAPI backend (WebSocket endpoints + HTTP routes)
from the outside using ``starlette.testclient.TestClient``. They are designed
to be runnable via the standard library only (``python3 -m unittest``) and
gracefully skip themselves when optional dependencies (``fastapi`` /
``httpx``) are not installed.
"""

