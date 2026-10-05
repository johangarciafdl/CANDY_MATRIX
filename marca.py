# marca.py
"""El logotipo "CANDY MATRIX" con letras de caramelo: cada letra en un color de
las frutas, con contorno grueso, sombra caída y brillo en la mitad superior.

Lo usan la cinemática (donde las letras caen una a una) y el menú principal,
para que el juego tenga una sola marca y no un título distinto en cada pantalla.
"""
import pygame

from config import COLOR_MAP
from fuentes import fuente, TITULO
from luces import guardado as _guardado, oscurecer as _oscurecer

TITULO_STR = "CANDY MATRIX"


# Paleta de caramelo para las letras, siguiendo los colores de las frutas.
ORDEN_COLORES = (0, 5, 3, 1, 2, None, 4, 6, 0, 5, 3, 1)


def letra_caramelo(c, color, tamano=104):
    """Letra de caramelo: contorno grueso, sombra caída y brillo superior."""
    def crear():
        f = fuente(TITULO, tamano)
        base = f.render(c, True, color)
        contorno_col = _oscurecer(color, 0.42)
        contorno = f.render(c, True, contorno_col)
        sombra = f.render(c, True, (16, 8, 26))
        g = 4  # grosor del contorno
        w, h = base.get_width() + 2 * g + 2, base.get_height() + 2 * g + 10
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        sombra.set_alpha(150)
        s.blit(sombra, (g, g + 8))
        for dx in range(-g, g + 1, 2):
            for dy in range(-g, g + 1, 2):
                if dx * dx + dy * dy <= g * g + 2:
                    s.blit(contorno, (g + dx, g + dy))
        s.blit(base, (g, g))
        # Brillo en la mitad superior, recortado a la forma de la letra: el
        # mínimo con la letra deja alfa 0 fuera de ella, y luego se pasa a blanco.
        banda = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(banda, (255, 255, 255, 80),
                         (0, 0, base.get_width(), int(base.get_height() * 0.48)))
        banda.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        banda.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_MAX)
        s.blit(banda, (g, g))
        return s
    return _guardado(('letra', c, color, tamano), crear)


def _colores_titulo():
    colores = []
    for idx in ORDEN_COLORES:
        colores.append(None if idx is None else COLOR_MAP[idx])
    return colores


def maqueta_titulo(tamano=104, espacio_extra=4):
    """Posición x de cada letra (respetando el ancho real de la fuente) y el
    título compuesto completo, que se usa una vez que todas han caído."""
    def crear():
        f = fuente(TITULO, tamano)
        colores = _colores_titulo()
        xs = []
        for i in range(len(TITULO_STR)):
            xs.append(f.size(TITULO_STR[:i])[0] + i * espacio_extra)
        letras = []
        for i, c in enumerate(TITULO_STR):
            if c == ' ':
                letras.append(None)
                continue
            letras.append(letra_caramelo(c, colores[i], tamano))
        ancho = xs[-1] + letras[-1].get_width()  # borde derecho real de la última letra
        alto = max(l.get_height() for l in letras if l)
        compuesto = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        for i, l in enumerate(letras):
            if l:
                compuesto.blit(l, (xs[i], 0))
        mascara = compuesto.copy()
        mascara.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_MAX)
        return xs, letras, compuesto, mascara
    return _guardado(('titulo', tamano), crear)


def titulo(tamano=104):
    """El logotipo completo ya compuesto, listo para blitear."""
    return maqueta_titulo(tamano)[2]
