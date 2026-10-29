from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
import urllib.parse

HOST = "127.0.0.1"
PORT = 8000


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.getcwd(), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/__live-reload-check":
            query = urllib.parse.parse_qs(parsed.query)
            requested = query.get("path", [""])[0]
            if not requested:
                self.send_response(400)
                self.end_headers()
                return

            target = os.path.abspath(os.path.join(os.getcwd(), requested.lstrip("/")))
            if os.path.exists(target):
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(str(int(os.path.getmtime(target) * 1000)).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
            return

        return super().do_GET()

    def send_head(self):
        requested_path = self.path
        if requested_path == "/":
            requested_path = "/index.html"

        file_path = self.translate_path(requested_path)
        if os.path.isfile(file_path) and (requested_path.lower().endswith(".html") or requested_path == "/index.html"):
            try:
                with open(file_path, "rb") as f:
                    content = f.read()

                reload_script = b'''
<script>
(function() {
  const listenerPath = window.location.pathname === "/" ? "/index.html" : window.location.pathname;
  window.__portfolioMtime = window.__portfolioMtime ?? null;
  const check = () => {
    fetch("/__live-reload-check?path=" + encodeURIComponent(listenerPath) + "&t=" + Date.now(), { cache: "no-store" })
      .then(response => response.text())
      .then(value => {
        const mtime = Number(value);
        if (!Number.isNaN(mtime) && mtime !== window.__portfolioMtime) {
          window.__portfolioMtime = mtime;
          window.location.reload();
        }
        window.__portfolioMtime = Number.isNaN(mtime) ? window.__portfolioMtime : mtime;
      })
      .catch(() => {});
  };
  setInterval(check, 1000);
})();
</script>
'''

                if b"</body>" in content.lower():
                    content = content.replace(b"</body>", reload_script + b"</body>")

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return None
            except OSError:
                pass

        return super().send_head()


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving portfolio at http://{HOST}:{PORT}")
    server.serve_forever()
