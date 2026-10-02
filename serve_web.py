# serve_web.py
"""Sirve la versión web ya compilada, para probarla en el navegador.

No se usa `python -m http.server` a secas porque el runtime de pygbag necesita
las cabeceras de aislamiento de origen (COOP/COEP): sin ellas el navegador no
habilita SharedArrayBuffer y el .wasm no llega a arrancar — la pantalla se queda
en negro sin un error claro.

Tampoco se usa el servidor de pygbag directamente porque ese recompila el
proyecto cada vez; esto solo sirve lo que ya hay en web/build/web.

Uso:
    .venv\\Scripts\\python build_web.py      # compilar primero
    .venv\\Scripts\\python serve_web.py      # luego servir en :8000

Para que lo abran desde otro dispositivo (un celular en la misma red, o un
compañero por internet), ver las notas de despliegue en README_WEB.md.
"""
import argparse
import functools
import http.server
import os
import socket
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(RAIZ, "web", "build", "web")


class Handler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler + las cabeceras que pide el runtime de pygbag."""

    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Access-Control-Allow-Origin", "*")
        # El .apk cambia en cada compilación; sin esto el navegador reutiliza
        # el anterior y parece que los cambios no se aplicaron.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, formato, *args):
        # Una línea por petición, sin la marca de tiempo que no aporta aquí.
        sys.stderr.write("  %s\n" % (formato % args))


def ip_local():
    """IP de esta máquina en la red local, para abrirlo desde el celular."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no envía nada, solo elige la interfaz
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--todas-las-interfaces", action="store_true",
                    help="escuchar en 0.0.0.0 para abrirlo desde otro dispositivo de la red")
    args = ap.parse_args()

    if not os.path.isdir(SALIDA):
        sys.exit("No hay nada compilado en %s\nEjecuta primero: python build_web.py" % SALIDA)

    host = "0.0.0.0" if args.todas_las_interfaces else "127.0.0.1"
    # directory= evita que el proceso se meta dentro de la carpeta: en Windows
    # eso la deja bloqueada y la siguiente compilación no puede borrarla.
    handler = functools.partial(Handler, directory=SALIDA)

    servidor = http.server.ThreadingHTTPServer((host, args.puerto), handler)
    print("Sirviendo %s" % SALIDA)
    print("  local:  http://localhost:%d" % args.puerto)
    if args.todas_las_interfaces:
        ip = ip_local()
        if ip:
            print("  red:    http://%s:%d   (celular/tablet en el mismo wifi)" % (ip, args.puerto))
    print("Ctrl+C para detener.\n")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")
        servidor.server_close()


if __name__ == "__main__":
    main()
