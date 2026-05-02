"""
server.py  —  CodeBreaker Local Game Server
=============================================
Starts a localhost HTTP server, serves the GUI (index.html),
and exposes a JSON API the frontend uses to talk to the game engine.

Run:   python main.py
       (which calls this via launch())
"""

from __future__ import annotations
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from engine import Engine


# One engine instance shared across all requests (single-player game)
_engine: Engine | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine


# ── Request handler ───────────────────────────────────────────────────────────

class GameHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass   # suppress request noise in terminal

    # ── routing ───────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_file("index.html", "text/html")
        elif path == "/api/state":
            self._api_state()
        elif path == "/api/reset":
            global _engine
            _engine = Engine()
            self._json({"ok": True})
        else:
            self._404()

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path == "/api/run":
            length  = int(self.headers.get("Content-Length", 0))
            body    = self.rfile.read(length)
            payload = json.loads(body)
            cmd     = payload.get("cmd", "")
            self._api_run(cmd)
        elif path == "/api/tab":
            length  = int(self.headers.get("Content-Length", 0))
            body    = self.rfile.read(length)
            payload = json.loads(body)
            partial = payload.get("partial", "")
            e = _get_engine()
            suggestions = e.tab_complete(partial)
            self._json({"suggestions": suggestions})
        else:
            self._404()

    # ── API handlers ──────────────────────────────────────────────────

    def _api_run(self, cmd: str):
        e      = _get_engine()
        lines  = e.run(cmd)
        state  = self._build_state(e)
        self._json({
            "lines":    [{"text": l.text, "style": l.style} for l in lines],
            "state":    state,
            "gameOver": e.game_over,
            "gameWon":  e.game_won,
        })

    def _api_state(self):
        e = _get_engine()
        self._json(self._build_state(e))

    def _build_state(self, e: Engine) -> dict:
        m     = e.current_mission()
        objs  = []
        for i, (desc, _) in enumerate(m["objectives"]):
            objs.append({
                "desc": desc,
                "done": e._obj_done.get((m["id"], i), False),
            })
        # sidebar filesystem listing
        children = e.fs_trie.ls(e.cwd)
        fs_items = []
        for name in children:
            full = e.cwd.rstrip("/") + "/" + name
            is_f = e.fs_trie.is_file(full)
            fs_items.append({
                "name":   name,
                "isFile": is_f,
                "locked": e.fs_trie.is_locked(full) if is_f else False,
            })
        return {
            "cwd":           e.cwd,
            "score":         e.score,
            "commandsRun":   e.commands_run,
            "missionTitle":  m["title"],
            "missionBrief":  m["brief"],
            "missionId":     m["id"],
            "objectives":    objs,
            "unlocked":      list(e.unlocked_rewards),
            "fsItems":       fs_items,
            "puzzleActive":  e.puzzle_active,
        }

    # ── helpers ───────────────────────────────────────────────────────

    def _serve_file(self, filename: str, mime: str):
        here = os.path.dirname(os.path.abspath(__file__))
        fp   = os.path.join(here, filename)
        try:
            with open(fp, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self._404()

    def _json(self, obj: dict):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def _404(self):
        self.send_response(404)
        self.end_headers()


# ── Public launch API ─────────────────────────────────────────────────────────

PORT = 7474

def launch():
    """Start the server and open the browser. Blocks until Ctrl+C."""
    global _engine
    _engine = Engine()

    server = HTTPServer(("127.0.0.1", PORT), GameHandler)
    url    = f"http://127.0.0.1:{PORT}/"

    print(f"\n  ⬡  CodeBreaker starting on {url}")
    print("  Opening browser... (Ctrl+C to quit)\n")

    # Open browser after a short delay so server is ready
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Connection terminated. Stay dark.")
        server.shutdown()
