# fruits.py
"""Sprites de frutas dibujados con primitivas de pygame y cacheados.

Cada sprite se rasteriza UNA sola vez por (tipo, radio) y luego solo se hace blit,
así el tablero completo cuesta 64 blits por frame en vez de cientos de llamadas de
dibujo. El número del valor va horneado dentro del sprite porque el valor de la
celda y el tipo de fruta son el mismo dato.
"""
import math
import pygame
from config import COLOR_MAP, BLANCO, font_large

_CACHE = {}

MARRON = (120, 78, 45)
VERDE_HOJA = (104, 187, 89)


def _oscurecer(color, f=0.3):
    return tuple(int(v * (1 - f)) for v in color)


def _brillo(surface, x, y, w, h):
    """Reflejo especular translúcido (le da el look brillante de caramelo/fruta)."""
    w, h = max(1, int(w)), max(1, int(h))
    capa = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(capa, (255, 255, 255, 115), capa.get_rect())
    surface.blit(capa, (int(x), int(y)))


def _hoja(surface, x, y, w, h):
    pygame.draw.ellipse(surface, VERDE_HOJA, pygame.Rect(int(x), int(y), max(2, int(w)), max(2, int(h))))


# -------------------- FRUTAS --------------------
def _manzana(s, cx, cy, r, color):
    pygame.draw.line(s, MARRON, (cx, int(cy - r * 0.45)), (cx + 2, int(cy - r * 1.05)), max(2, r // 7))
    _hoja(s, cx + 2, cy - r * 1.1, r * 0.78, r * 0.4)
    pygame.draw.circle(s, color, (int(cx - r * 0.3), int(cy + r * 0.12)), int(r * 0.76))
    pygame.draw.circle(s, color, (int(cx + r * 0.3), int(cy + r * 0.12)), int(r * 0.76))
    pygame.draw.circle(s, color, (cx, int(cy + r * 0.28)), int(r * 0.78))
    _brillo(s, cx - r * 0.68, cy - r * 0.42, r * 0.5, r * 0.34)
    return int(r * 0.15)


def _pera(s, cx, cy, r, color):
    pygame.draw.line(s, MARRON, (cx, int(cy - r * 0.55)), (cx, int(cy - r * 1.05)), max(2, r // 7))
    _hoja(s, cx + 1, cy - r * 1.08, r * 0.7, r * 0.34)
    pygame.draw.circle(s, color, (cx, int(cy + r * 0.4)), int(r * 0.7))
    pygame.draw.circle(s, color, (cx, int(cy - r * 0.2)), int(r * 0.46))
    pygame.draw.circle(s, color, (cx, int(cy + r * 0.08)), int(r * 0.58))
    _brillo(s, cx - r * 0.52, cy - r * 0.05, r * 0.4, r * 0.5)
    return int(r * 0.28)


def _arandano(s, cx, cy, r, color):
    pygame.draw.circle(s, color, (cx, cy), int(r * 0.86))
    pygame.draw.circle(s, _oscurecer(color, 0.25), (cx, cy), int(r * 0.86), 2)
    corona = _oscurecer(color, 0.45)
    for k in range(5):
        a = -math.pi / 2 + k * (2 * math.pi / 5)
        px = cx + math.cos(a) * r * 0.28
        py = cy - r * 0.52 + math.sin(a) * r * 0.15
        pygame.draw.circle(s, corona, (int(px), int(py)), max(2, int(r * 0.12)))
    _brillo(s, cx - r * 0.6, cy - r * 0.28, r * 0.45, r * 0.3)
    return int(r * 0.12)


def _limon(s, cx, cy, r, color):
    cuerpo = pygame.Rect(int(cx - r * 0.86), int(cy - r * 0.6), int(r * 1.72), int(r * 1.2))
    punta = _oscurecer(color, 0.12)
    pygame.draw.polygon(s, punta, [(int(cx - r * 0.8), cy), (int(cx - r * 1.1), int(cy - r * 0.12)),
                                    (int(cx - r * 1.1), int(cy + r * 0.12))])
    pygame.draw.polygon(s, punta, [(int(cx + r * 0.8), cy), (int(cx + r * 1.1), int(cy - r * 0.12)),
                                    (int(cx + r * 1.1), int(cy + r * 0.12))])
    pygame.draw.ellipse(s, color, cuerpo)
    pygame.draw.ellipse(s, _oscurecer(color, 0.2), cuerpo, 2)
    _brillo(s, cx - r * 0.6, cy - r * 0.44, r * 0.62, r * 0.28)
    return 0


def _uva(s, cx, cy, r, color):
    pygame.draw.line(s, MARRON, (cx, int(cy - r * 0.72)), (cx, int(cy - r * 1.02)), max(2, r // 8))
    _hoja(s, cx + 1, cy - r * 1.08, r * 0.6, r * 0.3)
    rb = int(r * 0.3)
    for (dx, dy) in [(-0.5, -0.4), (0.0, -0.5), (0.5, -0.4), (-0.28, 0.02), (0.28, 0.02), (0.0, 0.48)]:
        px, py = int(cx + dx * r), int(cy + dy * r)
        pygame.draw.circle(s, color, (px, py), rb)
        pygame.draw.circle(s, _oscurecer(color, 0.28), (px, py), rb, 1)
    _brillo(s, cx - r * 0.68, cy - r * 0.55, rb * 0.9, rb * 0.65)
    return int(r * 0.05)


def _naranja(s, cx, cy, r, color):
    pygame.draw.line(s, MARRON, (cx, int(cy - r * 0.8)), (cx, int(cy - r * 1.0)), max(2, r // 8))
    _hoja(s, cx - r * 0.78, cy - r * 1.08, r * 0.72, r * 0.32)
    pygame.draw.circle(s, color, (cx, cy), int(r * 0.88))
    pygame.draw.circle(s, _oscurecer(color, 0.22), (cx, cy), int(r * 0.88), 2)
    poros = _oscurecer(color, 0.16)
    for (dx, dy) in [(-0.42, 0.38), (0.34, 0.46), (0.52, -0.12), (-0.52, -0.02)]:
        pygame.draw.circle(s, poros, (int(cx + dx * r), int(cy + dy * r)), max(1, int(r * 0.07)))
    _brillo(s, cx - r * 0.62, cy - r * 0.55, r * 0.5, r * 0.32)
    return int(r * 0.05)


def _sandia(s, cx, cy, r, color):
    centro_y = cy - r * 0.28

    def arco(radio):
        pasos = 18
        return [(int(cx + radio * math.cos(math.pi * k / pasos)),
                 int(centro_y + radio * math.sin(math.pi * k / pasos))) for k in range(pasos + 1)]

    pygame.draw.polygon(s, (76, 160, 74), arco(r * 1.0))
    pygame.draw.polygon(s, (242, 246, 236), arco(r * 0.87))
    pygame.draw.polygon(s, color, arco(r * 0.76))
    for (dx, dy) in [(-0.42, 0.3), (0.34, 0.3), (-0.04, 0.55)]:
        pygame.draw.ellipse(s, (45, 32, 30), pygame.Rect(int(cx + dx * r), int(centro_y + dy * r),
                                                          max(2, int(r * 0.13)), max(3, int(r * 0.19))))
    return int(r * 0.08)


_DIBUJANTES = [_manzana, _pera, _arandano, _limon, _uva, _naranja, _sandia]


# -------------------- CACHÉ DE SPRITES --------------------
def _render_fruta(tipo, radio):
    pad = max(6, int(radio * 0.5))
    lado = radio * 2 + pad * 2
    s = pygame.Surface((lado, lado), pygame.SRCALPHA)
    c = lado // 2
    desplazamiento = _DIBUJANTES[tipo](s, c, c, radio, COLOR_MAP[tipo])

    texto = str(tipo)
    sombra = font_large.render(texto, True, (30, 18, 12))
    frente = font_large.render(texto, True, BLANCO)
    s.blit(sombra, sombra.get_rect(center=(c + 2, c + desplazamiento + 2)))
    s.blit(frente, frente.get_rect(center=(c, c + desplazamiento)))
    return s


def get_fruit_sprite(tipo, radio):
    """Devuelve (y cachea) el sprite de la fruta con su número horneado."""
    clave = (tipo, radio)
    if clave not in _CACHE:
        _CACHE[clave] = _render_fruta(tipo, radio)
    return _CACHE[clave]


def precargar(radio):
    """Rasteriza todas las frutas de una vez, al arrancar, para que no haya tirones."""
    for tipo in range(len(COLOR_MAP)):
        get_fruit_sprite(tipo, radio)
