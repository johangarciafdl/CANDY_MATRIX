# build_web.py
"""Compila la versión web del juego (WebAssembly) con pygbag.

¿Por qué una carpeta intermedia en vez de ejecutar `pygbag .` directamente?
Porque pygbag empaqueta todo lo que encuentra junto a `main.py`, y esta carpeta
arrastra los restos del puerto a Unity que se descartó (`Unity/`, `Library/`,
`Temp/`, `Packages/`), informes y el entorno virtual. Un `.apk` así se pasa de
los 12 MB y el navegador tiene que descargarlo entero antes de que arranque el
juego. Armando primero una copia limpia con solo los módulos y los sonidos, el
paquete baja a unos pocos cientos de kilobytes y el resultado es reproducible,
sin depender de la semántica de exclusión de pygbag.

Uso:
    .venv\\Scripts\\python build_web.py            # compila
    .venv\\Scripts\\python build_web.py --servir   # compila y sirve en :8000

El resultado queda en  web/build/web/  (index.html + candy_matrix.apk).
"""
import argparse
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.join(RAIZ, "web")

# Módulos que el juego necesita en el navegador. Se listan de forma explícita
# (en vez de copiar *.py) para que ni este script ni utilidades sueltas acaben
# dentro del paquete que descarga el estudiante.
MODULOS = [
    "main.py",
    "config.py",
    "matrix_logic.py",
    "sound_manager.py",
    "entrada.py",
    "fruits.py",
    "animations.py",
    "effects.py",
    "lore.py",
    "ui.py",
    "intro.py",
    "login.py",
    "hub.py",
    "level_map.py",
    "learn_zone.py",
    "skills.py",
    "boss.py",
    "quiz_system.py",
    "progress.py",
    "topics.py",
    "excel_exporter.py",
    "matrix_game.py",
    "vector_game.py",
    "system_game.py",
]


def verificar_dependencias():
    """Comprueba que MODULOS sea cerrado: nada que se importe puede faltar.

    Olvidar un módulo no rompe la compilación, solo la partida: el paquete se
    genera igual y el fallo aparece como un ImportError en la consola del
    navegador, donde cuesta mucho más verlo. Por eso se revisa aquí, leyendo los
    import de cada archivo con el propio parser de Python.
    """
    import ast

    incluidos = {os.path.splitext(m)[0] for m in MODULOS}
    locales = {os.path.splitext(f)[0] for f in os.listdir(RAIZ) if f.endswith(".py")}
    faltantes = {}

    for modulo in MODULOS:
        arbol = ast.parse(open(os.path.join(RAIZ, modulo), encoding="utf-8").read(), modulo)
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                nombres = [a.name.split(".")[0] for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nombres = [nodo.module.split(".")[0]] if nodo.module else []
            else:
                continue
            for nombre in nombres:
                # Solo interesan los módulos propios del proyecto: los de la
                # librería estándar y pygame los resuelve el runtime web.
                if nombre in locales and nombre not in incluidos:
                    faltantes.setdefault(nombre, []).append(modulo)

    if faltantes:
        detalle = "; ".join("%s.py (lo importa %s)" % (n, ", ".join(sorted(set(v))))
                            for n, v in sorted(faltantes.items()))
        sys.exit("Faltan módulos en MODULOS: %s" % detalle)
    print("Dependencias verificadas: %d módulos, ninguno suelto" % len(MODULOS))


def verificar_entrada():
    """Nadie debe leer los eventos salteándose entrada.py.

    En el celular SDL entrega los toques como FINGERDOWN, no como clics. El
    módulo `entrada` los traduce, pero una pantalla nueva que llame directamente
    a `pygame.event.get()` no recibiría ni un solo toque — y no daría ningún
    error: simplemente no respondería nada, que es exactamente el síntoma que
    costó encontrar la primera vez. Por eso se comprueba al compilar.
    """
    culpables = []
    for modulo in MODULOS:
        if modulo == "entrada.py":
            continue  # es quien los lee de verdad
        texto = open(os.path.join(RAIZ, modulo), encoding="utf-8").read()
        for llamada in ("pygame.event.get(", "pygame.mouse.get_pos("):
            if llamada in texto:
                culpables.append("%s usa %s)" % (modulo, llamada))

    if culpables:
        sys.exit("Eventos sin traducir (el táctil no funcionará):\n  "
                 + "\n  ".join(culpables)
                 + "\nUsa entrada.obtener_eventos() y entrada.posicion_puntero().")
    print("Entrada verificada: todo pasa por entrada.py")


def preparar_staging():
    """Copia los módulos y los sonidos .ogg a una carpeta limpia."""
    if os.path.isdir(STAGING):
        shutil.rmtree(STAGING)
    os.makedirs(os.path.join(STAGING, "assets", "sounds"))

    faltantes = [m for m in MODULOS if not os.path.exists(os.path.join(RAIZ, m))]
    if faltantes:
        sys.exit("Faltan módulos: %s" % ", ".join(faltantes))

    for modulo in MODULOS:
        shutil.copy2(os.path.join(RAIZ, modulo), os.path.join(STAGING, modulo))

    # Solo .ogg: es el único formato que el mixer de SDL reproduce de forma
    # fiable en el navegador, y sound_manager.py ya lo prefiere sobre .wav.
    origen_sonidos = os.path.join(RAIZ, "assets", "sounds")
    oggs = sorted(f for f in os.listdir(origen_sonidos) if f.endswith(".ogg"))
    if not oggs:
        sys.exit("No hay sonidos .ogg. Ejecuta primero convert_audio.py")
    for nombre in oggs:
        shutil.copy2(os.path.join(origen_sonidos, nombre),
                     os.path.join(STAGING, "assets", "sounds", nombre))

    print("Staging listo: %d módulos, %d sonidos" % (len(MODULOS), len(oggs)))


def compilar(servir):
    entorno = dict(os.environ)
    # pygbag 0.9.3 lee main.py con la codificación local; en Windows eso es
    # cp1252 y falla con la "Á" de "Álgebra Lineal". Forzar UTF-8 lo evita.
    entorno["PYTHONUTF8"] = "1"

    cmd = [sys.executable, "-m", "pygbag", "--title", "Candy Matrix"]
    if not servir:
        cmd.append("--build")
    cmd.append(STAGING)

    print("Ejecutando:", " ".join(cmd))
    return subprocess.call(cmd, cwd=RAIZ, env=entorno)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--servir", action="store_true",
                    help="tras compilar, levantar el servidor de prueba en :8000")
    args = ap.parse_args()

    verificar_dependencias()
    verificar_entrada()
    preparar_staging()
    codigo = compilar(args.servir)
    if codigo == 0 and not args.servir:
        salida = os.path.join(STAGING, "build", "web")
        print("\nListo ->", salida)
        if os.path.isdir(salida):
            for nombre in sorted(os.listdir(salida)):
                ruta = os.path.join(salida, nombre)
                print("  %-28s %8.1f KB" % (nombre, os.path.getsize(ruta) / 1024))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
