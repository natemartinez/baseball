import base64
import json
import os
import queue
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("YAHOO_CLIENT_ID")
CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET")

_REDIRECT_URI = "http://localhost:3001"
_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
_TOKENS_FILE = Path(__file__).parent / ".yahoo_tokens.json"
_SCOPES = "fspt-r"   # change to "fspt-w" if you need write

def _basic_auth_header():
    raw = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded = base64.b64encode(raw.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}

def _save(tokens: dict):
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
    _TOKENS_FILE.write_text(json.dumps(tokens, indent=2))

def _load() -> dict | None:
    if not _TOKENS_FILE.exists():
        return None
    return json.loads(_TOKENS_FILE.read_text())

def _exchange_code(code: str) -> dict:
    resp = requests.post(
        _TOKEN_URL,
        headers={**_basic_auth_header(), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "redirect_uri": _REDIRECT_URI, "code": code},
    )
    resp.raise_for_status()
    tokens = resp.json()
    _save(tokens)
    return tokens

def _refresh(refresh_token: str) -> dict:
    resp = requests.post(
        _TOKEN_URL,
        headers={**_basic_auth_header(), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "redirect_uri": _REDIRECT_URI, "refresh_token": refresh_token},
    )
    resp.raise_for_status()
    tokens = resp.json()
    _save(tokens)
    return tokens

def get_access_token() -> str:
    tokens = _load()
    if tokens is None:
        raise RuntimeError("Not authenticated. Run: python yahoo_auth.py")
    if tokens.get("expires_at", 0) < time.time() + 60:
        tokens = _refresh(tokens["refresh_token"])
    return tokens["access_token"]

def _wait_for_code() -> str:
    code_queue = queue.Queue()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                code_queue.put(params["code"][0])
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>Authentication successful! You can close this tab.</h2>")
            else:
                self.send_response(400)
                self.end_headers()
        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 3001), _Handler)
    thread = threading.Thread(target=server.handle_request)
    thread.daemon = True
    thread.start()

    try:
        return code_queue.get(timeout=120)
    except queue.Empty:
        raise RuntimeError("Timed out (2 min) waiting for Yahoo to redirect.")
    finally:
        server.server_close()

def run_auth_flow():
    client_id_encoded = urllib.parse.quote(CLIENT_ID, safe="")
    auth_url = (
        f"{_AUTH_URL}"
        f"?client_id={client_id_encoded}"
        f"&redirect_uri={_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={_SCOPES}"
    )

    print("\n=== Yahoo OAuth Setup ===")
    print("Opening browser...")
    webbrowser.open(auth_url)
    print("Waiting for redirect...")
    code = _wait_for_code()
    tokens = _exchange_code(code)
    print(f"\n✅ Authenticated! Token saved to {_TOKENS_FILE}")

if __name__ == "__main__":
    run_auth_flow()