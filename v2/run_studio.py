"""Run Caption Forge with an in-process, graceful quit hook."""
from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn

from server import app

HOST = "127.0.0.1"
PORT = 8878
URL = f"http://{HOST}:{PORT}"

server = uvicorn.Server(
    uvicorn.Config(app, host=HOST, port=PORT, log_level="warning", access_log=False)
)
app.state.uvicorn_server = server


def open_studio_when_ready() -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not server.should_exit:
        if server.started:
            webbrowser.open(URL)
            return
        time.sleep(0.1)


threading.Thread(target=open_studio_when_ready, daemon=True).start()
server.run()
