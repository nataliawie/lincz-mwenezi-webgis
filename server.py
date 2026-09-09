#!/usr/bin/env python3
"""
Servidor HTTP local com suporte completo a Range Requests (HTTP Byte Serving).
Necessário para servir arquivos .pmtiles corretamente, já que o pmtiles.js
faz requisições parciais (Range) para buscar apenas os tiles necessários
dentro do arquivo, em vez de baixar o arquivo inteiro.

Uso:
    python3 server.py [porta]

Exemplo:
    python3 server.py 8081
"""

import sys
import os
import http.server
import socketserver
import re
from email.utils import formatdate
import mimetypes

mimetypes.add_type("application/octet-stream", ".pmtiles")


class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP que responde corretamente a requisições Range (206 Partial Content)."""

    def send_head(self):
        path = self.translate_path(self.path)

        if os.path.isdir(path):
            return super().send_head()

        if not os.path.exists(path):
            self.send_error(404, "File not found")
            return None

        file_size = os.path.getsize(path)
        range_header = self.headers.get("Range")

        ctype = self.guess_type(path)

        if range_header:
            match = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if not match:
                self.send_error(416, "Invalid Range header")
                return None

            start_str, end_str = match.groups()

            if start_str == "" and end_str == "":
                self.send_error(416, "Invalid Range header")
                return None

            if start_str == "":
                # sufixo: últimos N bytes
                length = int(end_str)
                start = max(file_size - length, 0)
                end = file_size - 1
            else:
                start = int(start_str)
                end = int(end_str) if end_str != "" else file_size - 1

            if start >= file_size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{file_size}")
                self.end_headers()
                return None

            end = min(end, file_size - 1)
            length = end - start + 1

            f = open(path, "rb")
            f.seek(start)

            self.send_response(206)
            self.send_header("Content-type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(length))
            self.send_header("Last-Modified", self.date_time_string(os.stat(path).st_mtime))
            self.end_headers()

            return (f, length)

        else:
            f = open(path, "rb")
            self.send_response(200)
            self.send_header("Content-type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(file_size))
            self.send_header("Last-Modified", self.date_time_string(os.stat(path).st_mtime))
            self.end_headers()
            return (f, file_size)

    def copyfile_range(self, source, outputfile, length):
        remaining = length
        buf_size = 64 * 1024
        while remaining > 0:
            chunk = source.read(min(buf_size, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)

    def do_GET(self):
        result = self.send_head()
        if result is None:
            return
        if isinstance(result, tuple):
            f, length = result
            try:
                self.copyfile_range(f, self.wfile, length)
            finally:
                f.close()
        else:
            # Parent class already sent headers itself (e.g. directory
            # index lookup / listing) and just gave us a file-like object
            # to stream until EOF.
            try:
                self.copyfile(result, self.wfile)
            finally:
                result.close()

    def do_HEAD(self):
        result = self.send_head()
        if result is None:
            return
        if isinstance(result, tuple):
            result[0].close()
        else:
            result.close()

    def end_headers(self):
        # Habilita CORS, útil para requisições cross-origin (ex.: maplibre-gl / pmtiles.js)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type")
        self.send_header("Access-Control-Expose-Headers", "Content-Length, Content-Range, Accept-Ranges")
        super().end_headers()


def main():
    port = 8081
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Porta inválida: {sys.argv[1]}")
            sys.exit(1)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", port), RangeRequestHandler) as httpd:
        print(f"Servindo {os.getcwd()} em http://localhost:{port}  (suporte a Range Requests ativado)")
        print("Pressione Ctrl+C para parar.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")


if __name__ == "__main__":
    main()
