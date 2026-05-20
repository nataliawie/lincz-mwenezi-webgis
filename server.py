#!/usr/bin/env python3
import http.server, os, sys

class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404)
            return None
        fs = os.fstat(f.fileno())
        file_size = fs[6]
        range_header = self.headers.get('Range')
        if range_header:
            ranges = range_header.strip().replace('bytes=', '')
            start, end = ranges.split('-')
            start = int(start) if start else 0
            end = int(end) if end else file_size - 1
            end = min(end, file_size - 1)
            length = end - start + 1
            f.seek(start)
            self.send_response(206)
            self.send_header('Content-Type', self.guess_type(path))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
            self.send_header('Content-Length', str(length))
            self.end_headers()
            return f
        else:
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(path))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(file_size))
            self.end_headers()
            return f

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
with http.server.HTTPServer(('', port), RangeRequestHandler) as httpd:
    print(f"Serving on http://localhost:{port}")
    httpd.serve_forever()
