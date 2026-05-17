#!/usr/bin/env python3
"""Simple API server for landing page. Serves recipe data and the HTML page."""
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path

RECIPES = json.loads(
    Path("D:/Softwares/每次菜谱/recipes.json").read_text(encoding="utf-8")
)
STATE_FILE = Path("D:/Softwares/每次菜谱/state.json")
LANDING_DIR = Path("D:/Softwares/每次菜谱/landing")


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/recipe":
            qs = parse_qs(parsed.query)
            dish_name = unquote(qs.get("dish", [""])[0])

            # Find recipe
            recipe = next((r for r in RECIPES if r["name"] == dish_name), None)

            # Load today's state for reason/tip
            state = {}
            if STATE_FILE.exists():
                state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

            result = {
                "dish": dish_name,
                "category": recipe["category"] if recipe else "",
                "difficulty": recipe["difficulty"] if recipe else 3,
                "ingredients": recipe["ingredients"] if recipe else [],
                "steps": recipe["steps"] if recipe else [],
                "reason": state.get("reason", ""),
                "tip": state.get("tip", ""),
                "bvid": state.get("bvid", ""),
                "author": state.get("author", ""),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps(result, ensure_ascii=False).encode("utf-8")
            )
            return

        # Serve static files from landing/
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                (LANDING_DIR / "index.html").read_bytes()
            )
            return

        super().do_GET()

    def log_message(self, format, *args):
        print(f"  [{self.log_date_time_string()}] {args[0]}")


def main():
    port = 8848
    print(f"Serving on http://localhost:{port}")
    print(f"Example: http://localhost:{port}/?dish=宫保鸡丁&bvid=BV1Vh4y1s7ER")
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
