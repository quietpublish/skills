#!/usr/bin/env python3
"""Minimal HTTP server with range request support for video seeking.

Python's built-in http.server does NOT support range requests, which means
browsers cannot seek within video files. This server handles Range headers
and returns 206 Partial Content responses, enabling full video seeking.

Usage:
  python3 serve.py [port] [directory]
  python3 serve.py 8765 /path/to/video/dir
"""

import http.server
import os
import sys


class RangeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().do_GET()

        file_size = os.path.getsize(path)
        range_header = self.headers.get("Range")

        if range_header is None:
            return super().do_GET()

        # Parse range header: "bytes=START-END"
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)
        content_length = end - start + 1

        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        with open(path, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(content_length))

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    directory = sys.argv[2] if len(sys.argv) > 2 else "."
    os.chdir(directory)
    with http.server.HTTPServer(("", port), RangeHTTPRequestHandler) as httpd:
        print(f"Serving on port {port} from {os.getcwd()}")
        httpd.serve_forever()
