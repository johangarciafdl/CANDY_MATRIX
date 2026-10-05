# fuentes.py
"""Tipografía del juego: fuentes incluidas y respaldo para símbolos matemáticos.

¿Por qué incluir fuentes en vez de usar las del sistema?
    En el navegador (WebAssembly) no hay fuentes del sistema. `SysFont('arial')`
    no encuentra nada y cae a la fuente por defecto de pygame, que es un 30 %
    más estrecha y apretada: el juego se veía distinto en el celular que en el
    computador, y todo lo que se diseñaba mirando el escritorio salía mal en la
    web. Con las fuentes dentro del juego se ve idéntico en todas partes.

    - Fredoka (títulos y botones): redondeada, encaja con "Candy".
    - Nunito (texto): redondeada como Fredoka pero muy legible en tamaño chico.

¿Por qué un respaldo?
    pygame no hace "fallback" de fuentes: si un carácter no está en la fuente,
    dibuja un cuadrito. Fredoka y Nunito no traen λ, ←, →, ≠ ni ⟂, que el juego
    usa (λ para autovalores, ⟂ para vectores perpendiculares). `Fuente` reparte
    cada texto en tramos y dibuja los símbolos con Noto Sans Math, que solo
    incluye los signos de álgebra lineal para pesar 17 KB y no 780 KB.

Las fuentes están recortadas al alfabeto latino (ver RANGOS_PRINCIPALES): todo lo
demás va al respaldo. Licencia OFL; los avisos están en assets/fonts/.
"""
import os

import pygame

_CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")

TITULO = "Fredoka-700.ttf"
TITULO_SUAVE = "Fredoka-600.ttf"
TEXTO = "Nunito-600.ttf"
TEXTO_FUERTE = "Nunito-800.ttf"
SIMBOLOS = "NotoSansMath-simbolos.ttf"

# Caracteres que las CUATRO fuentes principales tienen de verdad, medidos con
# fontTools sobre sus tablas de caracteres (la intersección, porque un mismo
# texto puede dibujarse con cualquiera de ellas). Todo lo demás va al respaldo.
#
# No se puede suponer a partir de los bloques Unicode recortados: de los rangos
# pedidos, 215 caracteres no existen en estas fuentes (Fredoka no trae latín
# extendido, y falta mucha puntuación como ‖ o ′), y habrían salido como
# cuadritos. build_web.py vuelve a medir esto al compilar y falla si no coincide.
RANGOS_PRINCIPALES = (
    (0x0020, 0x007E), (0x00A0, 0x00AC), (0x00AE, 0x00FF), (0x0131, 0x0131),
    (0x0141, 0x0142), (0x0152, 0x0153), (0x0160, 0x0161), (0x0178, 0x0178),
    (0x017D, 0x017E), (0x2013, 0x2014), (0x2018, 0x201A), (0x201C, 0x201E),
    (0x2020, 0x2022), (0x2026, 0x2026), (0x2030, 0x2030), (0x2039, 0x203A),
    (0x2044, 0x2044), (0x20AC, 0x20AC), (0x2122, 0x2122),
)


def _en_principal(caracter):
    o = ord(caracter)
    return any(a <= o <= b for a, b in RANGOS_PRINCIPALES)


def _cargar(archivo, tamano):
    """Carga una fuente incluida; si falta el archivo, la de pygame por defecto,
    para que un asset perdido nunca impida arrancar el juego."""
    ruta = os.path.join(_CARPETA, archivo)
    try:
        return pygame.font.Font(ruta, tamano)
    except (FileNotFoundError, OSError, pygame.error):
        return pygame.font.Font(None, tamano)


class Fuente:
    """Se usa igual que `pygame.font.Font` (`render`, `size`, alturas), pero
    dibuja con la fuente de respaldo los caracteres que la principal no tiene."""

    def __init__(self, archivo, tamano):
        self.tamano = tamano
        self._principal = _cargar(archivo, tamano)
        self._respaldo = None  # se carga solo si algún texto lo necesita

    # -- API de pygame.font.Font que usa el juego ---------------------------
    def render(self, texto, antialias, color, background=None):
        tramos = self._tramos(texto)
        if len(tramos) == 1 and tramos[0][0] is self._principal:
            return self._render_simple(self._principal, texto, antialias, color, background)

        ascenso = max(f.get_ascent() for f, _ in tramos)
        descenso = max(-f.get_descent() for f, _ in tramos)
        piezas = [(f, self._render_simple(f, t, antialias, color, background)) for f, t in tramos]
        ancho = sum(p.get_width() for _, p in piezas)
        superficie = pygame.Surface((max(1, ancho), ascenso + descenso), pygame.SRCALPHA)
        if background is not None:
            superficie.fill(background)
        x = 0
        for f, pieza in piezas:
            # Alinear por la línea base, no por arriba: si no, λ quedaría
            # flotando más alto que las letras que la rodean.
            superficie.blit(pieza, (x, ascenso - f.get_ascent()))
            x += pieza.get_width()
        return superficie

    def size(self, texto):
        tramos = self._tramos(texto)
        if len(tramos) == 1:
            return tramos[0][0].size(texto)
        ancho = sum(f.size(t)[0] for f, t in tramos)
        alto = max(f.get_ascent() for f, _ in tramos) + max(-f.get_descent() for f, _ in tramos)
        return ancho, alto

    def get_height(self):
        return self._principal.get_height()

    def get_linesize(self):
        return self._principal.get_linesize()

    def get_ascent(self):
        return self._principal.get_ascent()

    def get_descent(self):
        return self._principal.get_descent()

    # -- interno ------------------------------------------------------------
    @staticmethod
    def _render_simple(f, texto, antialias, color, background):
        if background is None:
            return f.render(texto, antialias, color)
        return f.render(texto, antialias, color, background)

    def _tramos(self, texto):
        """Divide el texto en tramos consecutivos de una misma fuente."""
        if texto.isascii():  # el caso común, sin recorrer carácter a carácter
            return [(self._principal, texto)]
        tramos = []
        for c in texto:
            f = self._principal if _en_principal(c) else self._fuente_respaldo()
            if tramos and tramos[-1][0] is f:
                tramos[-1][1].append(c)
            else:
                tramos.append((f, [c]))
        return [(f, "".join(cs)) for f, cs in tramos] or [(self._principal, "")]

    def _fuente_respaldo(self):
        if self._respaldo is None:
            # Noto Sans Math tiene el ojo más chico que Nunito/Fredoka: un 10 %
            # más grande iguala visualmente la altura de los símbolos.
            self._respaldo = _cargar(SIMBOLOS, int(round(self.tamano * 1.1)))
        return self._respaldo


_CACHE = {}


def fuente(archivo, tamano):
    """Fuente compartida por (archivo, tamaño): cargar un TTF cuesta, y las
    pantallas piden la misma combinación muchas veces."""
    clave = (archivo, tamano)
    if clave not in _CACHE:
        _CACHE[clave] = Fuente(archivo, tamano)
    return _CACHE[clave]
