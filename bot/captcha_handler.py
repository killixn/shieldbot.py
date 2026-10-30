import json
import os
import secrets
import shutil
import subprocess
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

CHROME_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome")

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CAPTCHA</title>
  <script src="https://js.hcaptcha.com/1/api.js?render=explicit&onload=onLoad" async defer></script>
  <style>
    html, body { height: 100%; margin: 0; }
    body { display: flex; align-items: center; justify-content: center; }
  </style>
</head>
<body>
  <div id="captcha"></div>
  <script>
    const CFG = __CONFIG__;

    function onLoad() {
      const id = hcaptcha.render("captcha", { sitekey: CFG.sitekey, callback: send });
      if (CFG.rqdata) hcaptcha.setData(id, { rqdata: CFG.rqdata });
    }

    async function send(token) {
      try {
        await fetch("/" + CFG.nonce + "/solution", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        window.close();
      } catch (e) {
        console.error("token delivery failed:", e);
      }
    }
  </script>
</body>
</html>"""

def resolve_captcha(captcha_data: Mapping[str, Any], *, user_agent: str | None = None, proxy: str | None = None, timeout: float = 120) -> str:
    sitekey = captcha_data.get("captcha_sitekey")
    if not isinstance(sitekey, str) or not sitekey:
        raise ValueError("captcha_sitekey is missing from the Discord response")
    rqdata = captcha_data.get("captcha_rqdata")

    nonce = secrets.token_urlsafe(24)
    config = json.dumps({
        "sitekey": sitekey,
        "rqdata": rqdata if isinstance(rqdata, str) else None,
        "nonce": nonce,
    }).replace("</", "<\\/")
    page = PAGE.replace("__CONFIG__", config).encode()

    result: dict[str, str] = {}
    solved = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.split("?")[0] == f"/{nonce}/":
                self._reply(200, page, "text/html; charset=utf-8")
            else:
                self._reply(404, b"Not found")

        def do_POST(self) -> None:
            if self.path != f"/{nonce}/solution":
                return self._reply(404, b"Not found")
            try:
                length = min(int(self.headers.get("Content-Length", 0)), 64 * 1024)
                token = json.loads(self.rfile.read(length))["token"]
            except (ValueError, KeyError, TypeError):
                token = None
            if not isinstance(token, str) or not token:
                return self._reply(400, b'{"ok":false}', "application/json")
            result["token"] = token
            solved.set()
            self._reply(200, b'{"ok":true}', "application/json")

        def _reply(self, status: int, body: bytes, ctype: str = "text/plain") -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host = os.getenv("CAPTCHA_DISPLAY_HOST", "127.0.0.1")
    url = f"http://{host}:{server.server_port}/{nonce}/"
    # print(f"CAPTCHA opened in browser: {url}")

    with tempfile.TemporaryDirectory(prefix="captcha-chrome-", ignore_cleanup_errors=True) as profile:
        browser = _open_browser(url, host, profile, user_agent, proxy)
        try:
            if not solved.wait(timeout):
                raise TimeoutError("The CAPTCHA solving timeout was exceeded")
            return result["token"]
        finally:
            server.shutdown()
            server.server_close()
            if browser:
                browser.terminate()
                try:
                    browser.wait(5)
                except subprocess.TimeoutExpired:
                    browser.kill()


def _open_browser(url: str, host: str, profile: str, user_agent: str | None, proxy: str | None) -> subprocess.Popen | None:
    chrome = os.getenv("CHROMIUM_PATH") or next(filter(None, map(shutil.which, CHROME_NAMES)), None)

    if not chrome:
        if user_agent or proxy:
            raise RuntimeError("Chrome/Chromium is required to apply user_agent/proxy")
        webbrowser.open_new(url)
        return None

    cmd = [chrome, f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check", "--new-window"]
    if user_agent:
        cmd.append(f"--user-agent={user_agent}")
    if proxy:
        cmd.append(f"--proxy-server={proxy if '://' in proxy else 'http://' + proxy}")
        cmd.append(f"--proxy-bypass-list={host}")
    cmd.append(url)

    return subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
