import pytest
import subprocess
import time
import os
import signal
from pathlib import Path


TEST_PORT = 5001


_server_proc = None


def start_server():
    global _server_proc
    if _server_proc is not None:
        return

    project_root = Path(__file__).parent.parent
    venv_python = project_root / ".venv" / "bin" / "python"

    env = os.environ.copy()
    env["REDMINE_CLIENT"] = "mock"
    env["FLASK_ENV"] = "testing"

    _server_proc = subprocess.Popen(
        [str(venv_python), "-c", f"from app import app; app.run(port={TEST_PORT}, debug=False, threaded=True)"],
        cwd=str(project_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://localhost:{TEST_PORT}", timeout=1)
            print(f"Server started on port {TEST_PORT}")
            break
        except Exception:
            time.sleep(0.5)
    else:
        if _server_proc:
            _server_proc.terminate()
            _server_proc = None
        raise RuntimeError("Server failed to start")


def stop_server():
    global _server_proc
    if _server_proc:
        print("Stopping server")
        _server_proc.terminate()
        try:
            _server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_proc.kill()
            _server_proc.wait()
        _server_proc = None


@pytest.fixture(scope="session", autouse=True)
def app_server():
    start_server()
    yield
    stop_server()