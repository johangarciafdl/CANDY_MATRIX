# generar_sonidos.py
"""Sintetiza los efectos de sonido de la cinemática (assets/sounds/cine_*.ogg).

Se generan con código en vez de descargarlos: así no hay licencias de terceros
de por medio, y cada sonido está hecho a la medida de su momento de la historia.
Es una herramienta de desarrollo (necesita numpy y soundfile); el juego solo
usa los .ogg resultantes, que sí se publican.

    .venv\\Scripts\\python generar_sonidos.py

Recorrido sonoro (ver la línea de tiempo en intro.py):
    apertura      ambiente: colchón grave y misterioso que nace del silencio
    fragmentos    brillo_1..4: destellos de cristal (pentatónica de Re)
    convergencia  rafaga: viento que sube; encaje_1..2: clics al encajar
    la matriz     acorde: acorde cálido con golpe grave
    El Vacío      vacio: zumbido grave y disonante; grieta: crujidos
    ruptura       estallido: caída grave con cola de eco
    la chispa     chispa: encendido mágico; calidez: colchón esperanzador
    título        subida: silbido; letra_0..10: una nota por letra, en escala
                  ascendente; titulo: acorde final brillante

Todo en Re (re menor sus2 para el misterio, re mayor para la esperanza), para
que los sonidos combinen entre sí aunque se solapen.
"""
import os

import numpy as np
import soundfile as sf

# 22 050 Hz: de sobra para estos efectos (llegan hasta ~11 kHz) y pesan la
# mitad. Se sintetiza directamente a esta frecuencia, sin remuestrear.
SR = 22050
# Compresión Vorbis de 0 (máxima calidad) a 1 (mínimo tamaño). 0,8 no deja
# artefactos audibles en sonidos con eco y reduce el total a menos de la mitad:
# importa porque el juego web descarga los sonidos en cada publicación nueva.
COMPRESION = 0.8
CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sounds")
rng = np.random.default_rng(2026)  # semilla fija: el mismo resultado cada vez


# ==================== bloques básicos ====================
def tiempo(dur):
    return np.arange(int(SR * dur)) / SR


def nota(nombre):
    """'D4' -> Hz (afinación estándar, La4 = 440)."""
    semis = {'C': -9, 'C#': -8, 'D': -7, 'D#': -6, 'E': -5, 'F': -4, 'F#': -3,
             'G': -2, 'G#': -1, 'A': 0, 'A#': 1, 'B': 2}
    letra, octava = nombre[:-1], int(nombre[-1])
    return 440.0 * 2 ** ((semis[letra] + 12 * (octava - 4)) / 12)


def envolvente(n, ataque, caida_tau=None, sostener=None, relajar=0.0):
    """Ataque lineal; luego caída exponencial (tau) o meseta + relajación."""
    t = np.arange(n) / SR
    e = np.ones(n)
    if ataque > 0:
        e = np.minimum(e, t / ataque)
    if caida_tau:
        e = e * np.exp(-np.maximum(0, t - ataque) / caida_tau)
    if relajar > 0:
        fin = n / SR
        e = e * np.clip((fin - t) / relajar, 0, 1)
    return e


def campana(f, dur, tau=0.6, razon=3.5, indice=2.5, tau_indice=0.25):
    """Campana FM: inarmónica al golpe y más pura al apagarse (como el cristal)."""
    t = tiempo(dur)
    mod = indice * np.exp(-t / tau_indice) * np.sin(2 * np.pi * f * razon * t)
    return np.sin(2 * np.pi * f * t + mod) * np.exp(-t / tau)


def sierra_suave(f, t, armonicos=8):
    """Diente de sierra con pocos armónicos: cálido, sin aspereza."""
    return sum(np.sin(2 * np.pi * k * f * t) / k for k in range(1, armonicos + 1))


def ruido(n):
    return rng.standard_normal(n)


def paso_bajo(x, corte):
    """Filtro de un polo; `corte` en Hz, fijo o un arreglo (barrido)."""
    corte = np.broadcast_to(np.asarray(corte, dtype=float), x.shape)
    alfa = 1 - np.exp(-2 * np.pi * corte / SR)
    y = np.empty_like(x)
    acum = 0.0
    for i in range(len(x)):
        acum += alfa[i] * (x[i] - acum)
        y[i] = acum
    return y


def paso_alto(x, corte):
    return x - paso_bajo(x, corte)


def _peine(x, d, g):
    """y[n] = x[n] + g·y[n-d], por bloques de d muestras (rápido con numpy)."""
    y = x.copy()
    for ini in range(d, len(y), d):
        fin = min(ini + d, len(y))
        y[ini:fin] += g * y[ini - d:fin - d]
    return y


def _pasatodo(x, d, g):
    xd = np.concatenate([np.zeros(d), x[:-d]])
    y = -g * x + xd
    for ini in range(d, len(y), d):
        fin = min(ini + d, len(y))
        y[ini:fin] += g * y[ini - d:fin - d]
    return y


def reverberacion(x, mezcla=0.3, cola=1.6, brillo=0.82):
    """Reverberación de Schroeder (4 peines + 2 pasatodo). `cola` en segundos
    de silencio añadidos para que el eco se apague solo y no se corte."""
    # La parte "seca" se apaga en 60 ms antes de la cola de eco: si terminaba
    # de golpe (aún al 7-12 % de volumen) se oía un chasquido al final.
    x = fundidos(x, entrada=0, salida=0.06)
    x = np.concatenate([x, np.zeros(int(SR * cola))])
    retardos = [0.0297, 0.0371, 0.0411, 0.0437]
    humedo = sum(_peine(x, int(SR * r), brillo) for r in retardos) / len(retardos)
    for r, g in ((0.005, 0.7), (0.0017, 0.7)):
        humedo = _pasatodo(humedo, int(SR * r), g)
    humedo = paso_bajo(humedo, 5000)  # eco más oscuro que el sonido directo
    return (1 - mezcla) * x + mezcla * humedo


def normalizar(x, pico=0.75):
    """Pico al 75 %: la compresión Vorbis sobrepasa el pico original al
    decodificar, y con 0,89 algunos sonidos llegaban a saturar (1,04)."""
    x = x - np.mean(x)
    m = np.max(np.abs(x))
    return x * (pico / m) if m > 0 else x


def fundidos(x, entrada=0.003, salida=0.05):
    """Evita chasquidos al principio y al final."""
    n_in, n_out = int(SR * entrada), int(SR * salida)
    x = x.copy()
    if n_in:
        x[:n_in] *= np.linspace(0, 1, n_in)
    if n_out:
        x[-n_out:] *= np.linspace(1, 0, n_out)
    return x


def guardar(nombre, x):
    x = fundidos(normalizar(x))
    ruta = os.path.join(CARPETA, "cine_%s.ogg" % nombre)
    # (sf.write ignora compression_level; abriendo el archivo sí se aplica)
    with sf.SoundFile(ruta, "w", SR, 1, format="OGG", subtype="VORBIS",
                      compression_level=COMPRESION) as archivo:
        archivo.write(x.astype(np.float32))
    return ruta, len(x) / SR


# ==================== los sonidos ====================
def ambiente():
    """Apertura: colchón grave de re menor sus2 (sin tercera: ni triste ni
    alegre, solo misterioso) que nace del silencio y se abre poco a poco."""
    dur = 9.0
    t = tiempo(dur)
    x = np.zeros_like(t)
    for n, peso in (("D2", 1.0), ("A2", 0.8), ("D3", 0.6), ("E3", 0.45), ("A3", 0.35)):
        f = nota(n)
        for desafinar in (-0.004, 0.0, 0.0045):  # tres voces: efecto coro
            fase = rng.uniform(0, 2 * np.pi)
            x += peso * sierra_suave(f * (1 + desafinar), t + fase / (2 * np.pi * f), 6)
    # El filtro se abre (más brillo) y vuelve a cerrarse: el sonido "respira"
    corte = 260 + 1300 * np.sin(np.pi * np.clip(t / 7.5, 0, 1)) ** 2
    x = paso_bajo(x, corte)
    # Destellos agudos lejanos con trémolo lento, y "aire"
    brillo = sum(np.sin(2 * np.pi * nota(n) * t) * (0.5 + 0.5 * np.sin(2 * np.pi * v * t + p))
                 for n, v, p in (("D6", 0.23, 0.0), ("A6", 0.31, 1.7), ("E6", 0.17, 3.1)))
    aire = paso_bajo(paso_alto(ruido(len(t)), 2500), 6000)  # solo una banda, suave
    x = x / np.max(np.abs(x)) + 0.06 * brillo + 0.006 * aire
    x *= envolvente(len(t), 2.2, relajar=2.5)
    return reverberacion(x, 0.35, cola=1.0)


def brillo(f):
    """Un fragmento aparece: destello de cristal suave, con eco."""
    x = 0.8 * campana(f, 1.2, tau=0.45, razon=2.756, indice=1.6, tau_indice=0.08)
    x += 0.25 * campana(f * 2, 1.2, tau=0.25, razon=3.1, indice=1.0, tau_indice=0.05)
    return reverberacion(x, 0.45, cola=1.2)


def rafaga():
    """Convergencia: viento filtrado que sube de tono mientras las fichas
    vuelan hacia su lugar, con un fondo grave que crece."""
    dur = 1.7
    t = tiempo(dur)
    sube = np.clip(t / 1.25, 0, 1)
    corte_alto = 300 + 3400 * sube ** 2
    x = paso_bajo(ruido(len(t)), corte_alto)
    x = paso_alto(x, 150 + 900 * sube)
    amp = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5 * (0.4 + 0.6 * sube)
    grave = np.sin(2 * np.pi * (55 + 30 * sube) * t) * sube * 0.5
    return reverberacion(x * amp + grave * amp, 0.2, cola=0.6)


def encaje(f):
    """Una ficha encaja en su celda: clic corto, de cristal y madera."""
    t = tiempo(0.18)
    x = campana(f, 0.18, tau=0.045, razon=1.5, indice=3.0, tau_indice=0.01)
    golpe = paso_alto(ruido(len(t)), 2500) * np.exp(-t / 0.003)
    return reverberacion(x + 0.6 * golpe, 0.15, cola=0.25)


def acorde():
    """La matriz se completa: golpe grave y un acorde cálido de re mayor
    (con novena) que se abre con eco. Es la primera vez que suena 'mayor'."""
    dur = 3.4
    t = tiempo(dur)
    x = np.zeros_like(t)
    for n, peso in (("D3", 0.9), ("A3", 0.7), ("D4", 0.6), ("F#4", 0.55), ("E5", 0.25)):
        f = nota(n)
        x += peso * (sierra_suave(f, t, 5) * envolvente(len(t), 0.06, caida_tau=1.6))
        x += 0.35 * peso * campana(f * 2, dur, tau=1.0, razon=3.5, indice=1.2)
    x = paso_bajo(x, 2400)
    golpe = np.sin(2 * np.pi * 52 * t) * np.exp(-t / 0.35) * 2.2
    return reverberacion(x / np.max(np.abs(x)) + golpe, 0.38, cola=1.8)


def vacio():
    """El Vacío aparece: zumbido muy grave con batido (dos tonos casi iguales),
    un tritono encima (el intervalo más inestable) y un rugido que crece."""
    dur = 2.6
    t = tiempo(dur)
    f = 41.2  # mi grave, medio tono sobre re: choca con todo lo anterior
    x = np.sin(2 * np.pi * f * t) + 0.9 * np.sin(2 * np.pi * (f * 1.03) * t)
    x += 0.5 * sierra_suave(f * 2 ** (6 / 12) * 2, t, 6)  # tritono, una octava arriba
    rugido = paso_bajo(ruido(len(t)), 180 + 260 * (t / dur))
    x = paso_bajo(x, 400 + 900 * (t / dur) ** 2) + 2.2 * rugido
    # Aspiración: un ruido que crece al revés, como si tragara aire
    succion = paso_bajo(paso_alto(ruido(len(t)), 900), 3500) * (t / dur) ** 3
    x = x / np.max(np.abs(x)) + 0.07 * succion
    x *= envolvente(len(t), 1.6, relajar=0.5)
    return reverberacion(x, 0.3, cola=1.2)


def grieta():
    """Las grietas se extienden: crujidos secos cada vez más seguidos."""
    dur = 1.6
    n = int(SR * dur)
    x = np.zeros(n)
    t_golpes = np.sort(dur * rng.power(1.8, 46))  # sesgados hacia 1: más densos al final
    for tg in t_golpes:
        i = int(tg * SR)
        largo = int(SR * rng.uniform(0.004, 0.02))
        if i + largo >= n:
            continue
        r = paso_alto(ruido(largo), 1800) * np.exp(-np.arange(largo) / (SR * 0.004))
        x[i:i + largo] += r * rng.uniform(0.3, 1.0) * (0.4 + 0.6 * tg / dur)
    tt = tiempo(dur)
    tension = 0.08 * np.sin(2 * np.pi * 1760 * tt + 3 * np.sin(2 * np.pi * 7 * tt)) * (tt / dur) ** 2
    return reverberacion(x + tension, 0.25, cola=0.8)


def estallido():
    """La matriz estalla: chasquido inicial, caída grave de 90 a 28 Hz,
    ruido de la explosión y una cola de eco larga."""
    dur = 2.4
    t = tiempo(dur)
    frec = 28 + 62 * np.exp(-t / 0.35)
    fase = 2 * np.pi * np.cumsum(frec) / SR
    grave = np.sin(fase) * np.exp(-t / 0.9) * 1.6
    expl = paso_bajo(ruido(len(t)), 300 + 3500 * np.exp(-t / 0.25)) * np.exp(-t / 0.5)
    chasquido = paso_alto(ruido(len(t)), 1500) * np.exp(-t / 0.012) * 1.5
    x = grave + 1.3 * expl + chasquido
    return reverberacion(x, 0.42, cola=2.4, brillo=0.86)


def chispa():
    """La chispa se enciende: un suave 'fuuh' y luego un brillo mágico de
    notas agudas de re mayor que aparecen al azar, con un glissando que sube."""
    dur = 3.0
    t = tiempo(dur)
    soplo = paso_bajo(ruido(len(t)), 900) * np.exp(-((t - 0.12) / 0.09) ** 2)
    x = 1.4 * soplo
    pentatonica = ["D6", "E6", "F#6", "A6", "B6", "D7", "E7"]
    for k in range(16):
        inicio = 0.1 + 1.8 * (k / 16) + rng.uniform(-0.05, 0.05)
        f = nota(pentatonica[rng.integers(len(pentatonica))])
        c = campana(f, 1.0, tau=0.35, razon=2.756, indice=1.2, tau_indice=0.06)
        i = int(inicio * SR)
        x[i:i + len(c)] += c[:max(0, len(x) - i)] * rng.uniform(0.25, 0.6)
    gliss = np.sin(2 * np.pi * np.cumsum(500 * 2 ** (2 * np.clip(t / 2.0, 0, 1))) / SR)
    x += 0.12 * gliss * np.sin(np.pi * np.clip(t / 2.2, 0, 1))
    return reverberacion(x, 0.5, cola=1.6)


def calidez():
    """Bajo la chispa: colchón cálido de re mayor. Tras el Vacío, la primera
    sensación de esperanza."""
    dur = 3.8
    t = tiempo(dur)
    x = np.zeros_like(t)
    for n, peso in (("D3", 0.8), ("F#3", 0.6), ("A3", 0.6), ("D4", 0.5), ("A4", 0.25)):
        f = nota(n)
        for d in (-0.003, 0.003):
            x += peso * sierra_suave(f * (1 + d), t, 5)
    x = paso_bajo(x, 1100)
    x *= 0.85 + 0.15 * np.sin(2 * np.pi * 4.5 * t)  # trémolo suave, como un latido
    x *= envolvente(len(t), 1.3, relajar=1.4)
    return reverberacion(x, 0.35, cola=1.2)


def subida():
    """La chispa sube hasta el título: silbido que asciende."""
    dur = 0.9
    t = tiempo(dur)
    sube = np.clip(t / 0.7, 0, 1)
    x = paso_bajo(ruido(len(t)), 400 + 5000 * sube ** 1.5)
    x = paso_alto(x, 300 + 2500 * sube)
    tono = np.sin(2 * np.pi * np.cumsum(300 * 2 ** (2 * sube)) / SR) * 0.35
    amp = np.sin(np.pi * np.clip(t / dur, 0, 1)) * (0.3 + 0.7 * sube)
    return reverberacion((x + tono) * amp, 0.3, cola=0.7)


def letra(f):
    """Una letra del título cae: 'bloop' de caramelo, con el tono que baja un
    poco al principio (como un golpecito en una gominola)."""
    dur = 0.45
    t = tiempo(dur)
    frec = f * (1 + 0.5 * np.exp(-t / 0.018))
    fase = 2 * np.pi * np.cumsum(frec) / SR
    x = np.sin(fase) + 0.3 * np.sin(2 * fase) + 0.12 * np.sin(3 * fase)
    x *= np.exp(-t / 0.13)
    x += 0.3 * campana(f * 2, dur, tau=0.12, razon=3.0, indice=1.0, tau_indice=0.02)
    return reverberacion(x, 0.25, cola=0.5)


def titulo():
    """CANDY MATRIX completo: arpegio rápido de campanas y un acorde de re
    mayor brillante que se sostiene, con chispitas encima."""
    dur = 3.2
    t = tiempo(dur)
    x = np.zeros_like(t)
    for k, n in enumerate(("D5", "F#5", "A5", "D6", "F#6")):
        c = campana(nota(n), 2.0, tau=0.8, razon=3.5, indice=1.6, tau_indice=0.08)
        i = int(SR * 0.07 * k)
        x[i:i + len(c)] += 0.6 * c[:max(0, len(x) - i)]
    pad = sum(p * sierra_suave(nota(n), t, 5) for n, p in (("D4", 0.7), ("F#4", 0.6), ("A4", 0.6), ("D5", 0.4)))
    pad = paso_bajo(pad, 2600) * envolvente(len(t), 0.25, relajar=1.6)
    x += 0.45 * pad / np.max(np.abs(pad))
    for _ in range(14):
        i = int(SR * rng.uniform(0.3, 2.2))
        c = campana(nota(rng.choice(["D7", "A6", "F#7", "E7"])), 0.5, tau=0.15, razon=2.756, indice=0.8)
        x[i:i + len(c)] += 0.12 * c[:max(0, len(x) - i)]
    return reverberacion(x, 0.4, cola=1.8)


# ==================== catálogo ====================
# Una nota por letra del título, subiendo por la pentatónica de re mayor
# (11 letras: C A N D Y  M A T R I X)
NOTAS_LETRAS = ["D5", "E5", "F#5", "A5", "B5", "D6", "E6", "F#6", "A6", "B6", "D7"]

CATALOGO = [("ambiente", ambiente)]
CATALOGO += [("brillo_%d" % (i + 1), (lambda f: (lambda: brillo(f)))(nota(n)))
             for i, n in enumerate(("A5", "D6", "F#6", "B5"))]
CATALOGO += [("rafaga", rafaga)]
CATALOGO += [("encaje_%d" % (i + 1), (lambda f: (lambda: encaje(f)))(nota(n)))
             for i, n in enumerate(("A6", "D7"))]
CATALOGO += [("acorde", acorde), ("vacio", vacio), ("grieta", grieta),
             ("estallido", estallido), ("chispa", chispa), ("calidez", calidez),
             ("subida", subida)]
CATALOGO += [("letra_%d" % i, (lambda f: (lambda: letra(f)))(nota(n)))
             for i, n in enumerate(NOTAS_LETRAS)]
CATALOGO += [("titulo", titulo)]


def main():
    total = 0
    for nombre, fabrica in CATALOGO:
        ruta, dur = guardar(nombre, fabrica())
        kb = os.path.getsize(ruta) / 1024
        total += kb
        print("  cine_%-12s %5.2f s  %6.1f KB" % (nombre, dur, kb))
    print("  %d sonidos, %.0f KB en total" % (len(CATALOGO), total))


if __name__ == "__main__":
    main()
