"""Servidor del frontend para desarrollo, en http://127.0.0.1:5500.

Es igual a `python -m http.server`, pero le pide al navegador no guardar los archivos en
caché: así, al editar un .js o un .html, basta con recargar la página para ver el cambio.

Uso, desde la carpeta frontend:
    ..\\backend\\venv\\Scripts\\python.exe servidor.py
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PUERTO = 5500


class SinCache(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    manejador = partial(SinCache, directory=str(Path(__file__).parent))
    with ThreadingHTTPServer(("127.0.0.1", PUERTO), manejador) as servidor:
        print(f"Frontend en http://127.0.0.1:{PUERTO}/login.html  (Ctrl+C para detener)")
        servidor.serve_forever()
