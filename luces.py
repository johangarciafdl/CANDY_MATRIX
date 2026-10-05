# luces.py
"""Luz, velos y curvas de animación compartidos por la cinemática y El Vacío.

La técnica: los resplandores son gradientes radiales sobre negro que se SUMAN
a la pantalla (BLEND_ADD). Sobre un fondo oscuro eso se ve como luz real, y es
barato: un resplandor de 600x600 cuesta ~0,45 ms. Lo caro en pygame son las
capas con alfa de pantalla completa (hasta 17 ms), así que aquí los velos
(oscurecer, destellar) multiplican o suman una tira reutilizada.

Todo lo costoso se crea una vez y se guarda en caché; los resplandores tienen
un presupuesto de memoria porque los que se animan de tamaño o intensidad
generan una copia por escalón, y el navegador no tiene memoria de sobra.
"""
from collections import OrderedDict
import math

import pygame

from config import Config

ANCHO, ALTO = Config.ANCHO, Config.ALTO


def ease(t):
    """Arranca y termina suave."""
    t = max(0.0, min(1.0, t))
    return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_out_back(t, s=1.9):
    """Pasa un poco de largo y vuelve: el 'rebote' de las letras al caer."""
    t = max(0.0, min(1.0, t))
    t -= 1
    return t * t * ((s + 1) * t + s) + 1


def fase(t, desde, hasta):
    """Progreso 0..1 de t dentro de [desde, hasta]."""
    if hasta <= desde:
        return 1.0
    return max(0.0, min(1.0, (t - desde) / (hasta - desde)))


def mezcla(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def oscurecer(color, k):
    return tuple(int(c * k) for c in color)


_cache = {}


def guardado(clave, fabrica):
    """Superficies caras se crean una vez y se reutilizan."""
    s = _cache.get(clave)
    if s is None:
        s = _cache[clave] = fabrica()
    return s


# Los resplandores van aparte y con presupuesto: los que cambian de tamaño o de
# intensidad (la chispa al encenderse, el pulso) generan una copia por cada
# escalón, y sin límite la caché pasaba de 40 MB, demasiado para el navegador.
# Se descartan los menos usados recientemente.
_halos = OrderedDict()


_PRESUPUESTO_PIXELES = 8_000_000  # ~32 MB a 32 bits por píxel


_pixeles_halos = 0


def gradiente_blanco(curva):
    """Gradiente radial blanco pequeño; se escala suavemente al tamaño pedido.
    Calcularlo píxel a píxel solo 64x64 y luego escalarlo es mucho más rápido
    que calcularlo al tamaño final, y el escalado suave no deja escalones."""
    def crear():
        n = 64
        s = pygame.Surface((n, n))
        c = (n - 1) / 2.0
        for y in range(n):
            for x in range(n):
                d = math.hypot(x - c, y - c) / c
                k = max(0.0, 1.0 - d) ** curva
                v = int(255 * k)
                s.set_at((x, y), (v, v, v))
        return s
    return guardado(('grad', curva), crear)


def halo(ancho, alto, color, curva):
    global _pixeles_halos
    s = pygame.transform.smoothscale(gradiente_blanco(curva), (ancho, alto)).convert()
    s.fill(color, special_flags=pygame.BLEND_MULT)
    _pixeles_halos += ancho * alto
    while _pixeles_halos > _PRESUPUESTO_PIXELES and len(_halos) > 1:
        _, viejo = _halos.popitem(last=False)  # el más antiguo
        _pixeles_halos -= viejo.get_width() * viejo.get_height()
    return s


def cuantizar(v):
    """Redondea un tamaño a escalones: finos si es pequeño (se notaría), gruesos
    si es grande (no se nota y ahorra copias en caché)."""
    paso = 2 if v < 24 else 8 if v < 120 else 24
    return max(paso, int(v) // paso * paso)


def luz(destino, x, y, radio, color, intensidad=1.0, curva=2.0, alto=None, niveles=16):
    """Suma un resplandor (BLEND_ADD): sobre el fondo oscuro se ve como luz.

    `radio` es la mitad del ancho y `alto` la mitad del alto (si se da, el
    resplandor es una elipse: así se hacen las estelas del destello).
    La intensidad se redondea a `niveles` escalones para acotar la caché.
    """
    k = int(intensidad * niveles + 0.5)
    if k <= 0 or radio <= 0:
        return
    if k > niveles:
        k = niveles
    rx = cuantizar(radio)
    ry = rx if alto is None else cuantizar(alto)
    # Se consulta la caché por los parámetros, sin calcular el color escalado:
    # esta función se llama cientos de veces por fotograma y en el caso común
    # (acierto) debe ser una sola búsqueda en un diccionario.
    clave = (rx, ry, color, k, niveles, curva)
    h = _halos.get(clave)
    if h is None:
        h = _halos[clave] = halo(rx * 2, ry * 2, oscurecer(color, k / niveles), curva)
    destino.blit(h, (int(x - rx), int(y - ry)), None, pygame.BLEND_ADD)


_TIRA_VELO = None


def velo(destino, gris, modo):
    """Oscurece (BLEND_MULT) o ilumina (BLEND_ADD) toda la pantalla.

    Una capa de pantalla completa con alfa costaba 6,2 ms; multiplicar por una
    tira de 1200x100 reutilizada, repetida 8 veces, cuesta la mitad, y sumar,
    un cuarto. (Hacerlo con `fill(..., BLEND_MULT)` es peor: 49 ms.)
    """
    global _TIRA_VELO
    if _TIRA_VELO is None:
        _TIRA_VELO = pygame.Surface((ANCHO, 100)).convert()
    _TIRA_VELO.fill(gris)
    destino.blits([(_TIRA_VELO, (0, y), None, modo) for y in range(0, ALTO, 100)], False)


def oscurecer_todo(destino, factor):
    """factor 1 = sin cambio, 0 = negro."""
    v = int(255 * max(0.0, min(1.0, factor)))
    if v < 255:
        velo(destino, (v, v, v), pygame.BLEND_MULT)


def multiplicar_todo(destino, color):
    """Multiplica cada canal por color/255: oscurece y tiñe a la vez (por
    ejemplo, hacia un violeta profundo en vez de hacia un gris)."""
    if tuple(color) != (255, 255, 255):
        velo(destino, tuple(int(c) for c in color), pygame.BLEND_MULT)


def iluminar_todo(destino, cantidad, color=(255, 246, 236)):
    """cantidad 0..1: destello que satura hacia `color`."""
    if cantidad > 0:
        velo(destino, oscurecer(color, min(1.0, cantidad)), pygame.BLEND_ADD)


def penumbra(destino, x, y, rx, ry, fuerza):
    """Oscurece suavemente una elipse (BLEND_MULT), sin capa con alfa: se usa
    detrás de los subtítulos para que se lean aunque pasen fichas por detrás."""
    nivel = int(fuerza * 8 + 0.5)
    if nivel <= 0:
        return
    def crear():
        g = pygame.transform.smoothscale(gradiente_blanco(1.3), (rx * 2, ry * 2)).convert()
        g.fill(oscurecer((255, 255, 255), 0.72 * nivel / 8), special_flags=pygame.BLEND_MULT)
        blanco = pygame.Surface((rx * 2, ry * 2)).convert()
        blanco.fill((255, 255, 255))
        blanco.blit(g, (0, 0), None, pygame.BLEND_SUB)
        return blanco
    sup = guardado(('penumbra', rx, ry, nivel), crear)
    destino.blit(sup, (x - rx, y - ry), None, pygame.BLEND_MULT)
