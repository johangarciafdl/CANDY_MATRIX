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
    "fuentes.py",
    "luces.py",
    "marca.py",
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


def verificar_sombras():
    """Ninguna variable puede llamarse igual que un módulo del proyecto importado.

    Pasó de verdad: `skills.py` hacía `import entrada` y, dentro del modal de
    pregunta, `entrada = time.time()`. A partir de esa línea `entrada` ya era un
    número, `entrada.obtener_eventos()` reventaba con AttributeError y ninguna
    habilidad se podía cargar. Python no avisa al importar ni al compilar: el
    error solo aparece al abrir esa pantalla concreta. Se comprueba aquí con el
    árbol sintáctico, que no necesita ejecutar nada.
    """
    import ast

    propios = {os.path.splitext(m)[0] for m in MODULOS}
    culpables = []

    for modulo in MODULOS:
        arbol = ast.parse(open(os.path.join(RAIZ, modulo), encoding="utf-8").read(), modulo)
        importados = set()
        for nodo in arbol.body:
            if isinstance(nodo, ast.Import):
                importados |= {a.asname or a.name for a in nodo.names if a.name in propios}

        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Store) and nodo.id in importados:
                culpables.append("%s:%d asigna a `%s`, que es un módulo importado"
                                 % (modulo, nodo.lineno, nodo.id))
            elif isinstance(nodo, ast.arg) and nodo.arg in importados:
                culpables.append("%s:%d tiene un parámetro llamado `%s`, que es un módulo importado"
                                 % (modulo, nodo.lineno, nodo.arg))

    if culpables:
        sys.exit("Variables que tapan un módulo (fallarán al ejecutarse):\n  "
                 + "\n  ".join(culpables))
    print("Nombres verificados: ninguna variable tapa un módulo importado")


def verificar_fuentes():
    """Ningún texto del juego puede quedar sin glifo (se vería un cuadrito).

    Comprueba dos cosas contra las tablas de caracteres reales de las fuentes:
      1. que RANGOS_PRINCIPALES de fuentes.py no prometa caracteres que las
         fuentes principales no tienen;
      2. que cada carácter que aparece en los textos del juego lo cubra la
         fuente principal o la de símbolos.
    Necesita fontTools (.venv\\Scripts\\pip install fonttools); sin él se avisa
    y se sigue, porque es una comprobación de calidad, no de funcionamiento.
    """
    import ast
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("AVISO: sin fontTools no se verifican los glifos (pip install fonttools)")
        return

    sys.path.insert(0, RAIZ)
    import fuentes

    carpeta = os.path.join(RAIZ, "assets", "fonts")
    principales = [fuentes.TITULO, fuentes.TITULO_SUAVE, fuentes.TEXTO, fuentes.TEXTO_FUERTE]
    comun = set.intersection(*[set(TTFont(os.path.join(carpeta, f)).getBestCmap())
                               for f in principales])
    respaldo = set(TTFont(os.path.join(carpeta, fuentes.SIMBOLOS)).getBestCmap())

    prometidos = {o for a, b in fuentes.RANGOS_PRINCIPALES for o in range(a, b + 1)}
    falsos = sorted(prometidos - comun)
    if falsos:
        sys.exit("RANGOS_PRINCIPALES incluye caracteres que las fuentes no tienen: %s"
                 % " ".join("U+%04X" % o for o in falsos[:20]))

    sin_glifo = {}
    for modulo in MODULOS:
        arbol = ast.parse(open(os.path.join(RAIZ, modulo), encoding="utf-8").read(), modulo)
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
                for c in nodo.value:
                    o = ord(c)
                    if o >= 0x20 and o not in prometidos and o not in respaldo:
                        sin_glifo.setdefault(c, set()).add(modulo)

    if sin_glifo:
        detalle = "; ".join("%r U+%04X en %s" % (c, ord(c), ", ".join(sorted(m)))
                            for c, m in sorted(sin_glifo.items()))
        sys.exit("Caracteres sin glifo en ninguna fuente (saldrían como cuadritos): " + detalle)
    print("Fuentes verificadas: todos los textos tienen glifo")


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

    # Fuentes: sin ellas el navegador cae a la fuente por defecto de pygame.
    # Se copian también los avisos de licencia OFL, que la licencia exige que
    # acompañen a las fuentes donde se redistribuyan.
    origen_fuentes = os.path.join(RAIZ, "assets", "fonts")
    destino_fuentes = os.path.join(STAGING, "assets", "fonts")
    os.makedirs(destino_fuentes)
    fuentes_copiadas = sorted(f for f in os.listdir(origen_fuentes) if f.endswith((".ttf", ".txt")))
    for nombre in fuentes_copiadas:
        shutil.copy2(os.path.join(origen_fuentes, nombre), os.path.join(destino_fuentes, nombre))

    print("Staging listo: %d módulos, %d sonidos, %d archivos de fuentes"
          % (len(MODULOS), len(oggs), len(fuentes_copiadas)))


# Archivos que la página necesita junto a index.html (no van dentro del .apk):
# el service worker que guarda el intérprete y la fuente del título de la
# pantalla de carga.
ESTATICOS = {
    "sw.js": os.path.join("web_static", "sw.js"),
    "Fredoka-700.ttf": os.path.join("assets", "fonts", "Fredoka-700.ttf"),
}


def copiar_estaticos():
    salida = os.path.join(STAGING, "build", "web")
    for nombre, origen in ESTATICOS.items():
        shutil.copy2(os.path.join(RAIZ, origen), os.path.join(salida, nombre))


def compilar(servir):
    entorno = dict(os.environ)
    # pygbag 0.9.3 lee main.py con la codificación local; en Windows eso es
    # cp1252 y falla con la "Á" de "Álgebra Lineal". Forzar UTF-8 lo evita.
    entorno["PYTHONUTF8"] = "1"

    # Plantilla propia (web_template.tmpl): pantalla de carga en español con
    # barra de progreso, registro del service worker y desbloqueo inmediato
    # del audio al tocar. La de pygbag ocultaba el progreso y solo decía
    # "Loading, please wait", así que parecía colgada.
    cmd = [sys.executable, "-m", "pygbag", "--title", "Candy Matrix",
           "--template", os.path.join(RAIZ, "web_template.tmpl")]
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
    verificar_sombras()
    verificar_fuentes()
    preparar_staging()
    codigo = compilar(args.servir)
    if codigo == 0:
        copiar_estaticos()
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
