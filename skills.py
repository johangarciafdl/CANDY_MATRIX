# skills.py
"""Habilidades especiales: se ganan respondiendo preguntas y tienen enfriamiento.

Cada habilidad traduce una idea de álgebra lineal a una acción en el tablero:
    Bomba    -> submatriz 3x3 alrededor de una celda
    Estrella -> fila y columna completas (operación elemental de fila/columna)
    Arcoíris -> todas las celdas con el mismo valor
"""
import entrada
import asyncio
import math
import time
import pygame

from config import Config, BLANCO, font, font_small, font_large
from ui import draw_button, texto
from quiz_system import pick_question

HABILIDADES = [
    {'id': 'bomba', 'nombre': 'Bomba', 'color': (198, 62, 52), 'cooldown': 25,
     'desc': 'Elimina la submatriz 3x3 alrededor de la celda que elijas.'},
    {'id': 'estrella', 'nombre': 'Estrella', 'color': (226, 164, 38), 'cooldown': 35,
     'desc': 'Elimina la fila y la columna completas: una operación elemental.'},
    {'id': 'arcoiris', 'nombre': 'Arcoíris', 'color': (126, 87, 194), 'cooldown': 45,
     'desc': 'Elimina todas las frutas que tengan el mismo valor.'},
]

_POR_ID = {h['id']: h for h in HABILIDADES}
_ICONOS = {}


# -------------------- ICONOS --------------------
def _puntos_estrella(cx, cy, r_ext, r_int, puntas=5):
    pts = []
    for k in range(puntas * 2):
        r = r_ext if k % 2 == 0 else r_int
        a = -math.pi / 2 + k * math.pi / puntas
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


_SUPERMUESTREO_ICONO = 3


def _icono(hid, lado=40):
    clave = (hid, lado)
    if clave in _ICONOS:
        return _ICONOS[clave]

    lado_hq = lado * _SUPERMUESTREO_ICONO
    s = pygame.Surface((lado_hq, lado_hq), pygame.SRCALPHA)
    c = lado_hq // 2
    r = lado_hq // 2 - 4 * _SUPERMUESTREO_ICONO

    if hid == 'bomba':
        pygame.draw.line(s, (150, 110, 60), (c + r * 0.4, c - r * 0.5), (c + r * 0.9, c - r * 1.0),
                         3 * _SUPERMUESTREO_ICONO)
        pygame.draw.circle(s, (255, 190, 60), (int(c + r * 0.95), int(c - r * 1.0)),
                           max(2, lado // 12) * _SUPERMUESTREO_ICONO)
        pygame.draw.circle(s, (45, 45, 55), (c, c + 2), int(r * 0.82))
        pygame.draw.circle(s, (110, 110, 125), (int(c - r * 0.3), int(c - r * 0.2)), max(2, int(r * 0.2)))
    elif hid == 'estrella':
        pygame.draw.polygon(s, (255, 208, 70), _puntos_estrella(c, c + 1, r * 0.95, r * 0.42))
        pygame.draw.polygon(s, (190, 130, 20), _puntos_estrella(c, c + 1, r * 0.95, r * 0.42),
                            2 * _SUPERMUESTREO_ICONO)
    else:  # arcoíris
        colores = [(226, 74, 74), (240, 160, 50), (245, 214, 70), (95, 190, 100), (70, 140, 225), (150, 95, 200)]
        for k, color in enumerate(colores):
            radio = r - k * max(2, r // 7)
            if radio <= 2:
                break
            rect = pygame.Rect(c - radio, c - radio + 6, radio * 2, radio * 2)
            pygame.draw.arc(s, color, rect, math.pi * 0.08, math.pi * 0.92, max(2, r // 7))

    s = pygame.transform.smoothscale(s, (lado, lado))
    _ICONOS[clave] = s
    return s


# -------------------- ESTADO --------------------
class SistemaHabilidades:
    """Máquina de carga/enfriamiento de habilidades, independiente del minijuego:
    cualquier módulo de tema le pasa su propia lista de habilidades (con 'id' y
    'cooldown') y este motor se encarga del resto."""

    def __init__(self, habilidades_def=None):
        self.habilidades_def = habilidades_def if habilidades_def is not None else HABILIDADES
        self._por_id = {h['id']: h for h in self.habilidades_def}
        self.datos = {h['id']: {'carga': 0, 'listo_en': 0.0} for h in self.habilidades_def}
        self.usos_nivel = 0

    def reiniciar_nivel(self):
        self.usos_nivel = 0
        for d in self.datos.values():
            d['carga'] = 0
            d['listo_en'] = 0.0

    def limite_alcanzado(self):
        return self.usos_nivel >= Config.MAX_SKILL_USES_PER_LEVEL

    def segundos_restantes(self, hid):
        return max(0.0, self.datos[hid]['listo_en'] - time.time())

    def estado_de(self, hid):
        """'limite' | 'enfriando' | 'lista' | 'sin_carga'"""
        if self.limite_alcanzado():
            return 'limite'
        if self.segundos_restantes(hid) > 0:
            return 'enfriando'
        if self.datos[hid]['carga'] > 0:
            return 'lista'
        return 'sin_carga'

    def otorgar(self, hid):
        self.datos[hid]['carga'] = 1

    def consumir(self, hid):
        self.datos[hid]['carga'] = 0
        self.datos[hid]['listo_en'] = time.time() + self._por_id[hid]['cooldown']
        self.usos_nivel += 1

    def posponer_enfriamientos(self, segundos):
        """Corre los enfriamientos cuando el juego estuvo pausado (pregunta o estudio)."""
        for d in self.datos.values():
            if d['listo_en'] > 0:
                d['listo_en'] += segundos


# -------------------- EFECTOS --------------------
def celdas_afectadas(hid, tablero, i, j):
    """Celdas que la habilidad eliminaría si se aplica en (i, j)."""
    if hid == 'bomba':
        return {(a, b)
                for a in range(i - 1, i + 2)
                for b in range(j - 1, j + 2)
                if 0 <= a < Config.FILAS and 0 <= b < Config.COLUMNAS}

    if hid == 'estrella':
        return ({(i, b) for b in range(Config.COLUMNAS)} |
                {(a, j) for a in range(Config.FILAS)})

    if hid == 'arcoiris':
        objetivo = tablero[i][j]
        return {(a, b)
                for a in range(Config.FILAS)
                for b in range(Config.COLUMNAS)
                if tablero[a][b] == objetivo}

    return set()


def descripcion(hid):
    return _POR_ID[hid]['desc']


def nombre(hid):
    return _POR_ID[hid]['nombre']


# -------------------- BARRA DE HABILIDADES --------------------
def get_barra_rects():
    ancho, alto, gap = 150, 74, 18
    total = len(HABILIDADES) * ancho + (len(HABILIDADES) - 1) * gap
    centro_x = Config.MARGEN_IZQUIERDO + (Config.COLUMNAS * Config.TAMANO_CELDA) // 2
    x0 = centro_x - total // 2
    # +44 deja el encabezado por debajo del marco del tablero, que termina en +14.
    y = Config.MARGEN_SUPERIOR + Config.FILAS * Config.TAMANO_CELDA + 44
    return {h['id']: pygame.Rect(x0 + k * (ancho + gap), y, ancho, alto)
            for k, h in enumerate(HABILIDADES)}


_BOTONES = {}


def _superficie_boton(h, base, etiqueta, activa, hover, tamano):
    """Los rectángulos redondeados son caros; cada combinación de estado se
    rasteriza una vez y después es un solo blit por frame."""
    clave = (h['id'], base, etiqueta, activa, hover)
    superficie = _BOTONES.get(clave)
    if superficie is not None:
        return superficie

    if len(_BOTONES) > 200:
        _BOTONES.clear()

    ancho, alto = tamano
    superficie = pygame.Surface((ancho, alto + 4), pygame.SRCALPHA)
    cuerpo = pygame.Rect(0, 0, ancho, alto)
    color = tuple(min(255, int(c * 1.18)) for c in base) if hover else base

    pygame.draw.rect(superficie, tuple(int(c * 0.45) for c in base), cuerpo.move(0, 4), border_radius=14)
    pygame.draw.rect(superficie, color, cuerpo, border_radius=14)
    pygame.draw.rect(superficie, (255, 226, 90) if activa else BLANCO, cuerpo,
                     4 if activa else 3, border_radius=14)

    icono = _icono(h['id'], 40)
    superficie.blit(icono, icono.get_rect(center=(30, alto // 2)))
    superficie.blit(texto(font_small, h['nombre'], BLANCO), (56, 16))
    superficie.blit(texto(font, etiqueta, BLANCO), (56, 38))

    _BOTONES[clave] = superficie
    return superficie


def draw_barra(ventana, sistema, seleccionada, mouse_pos):
    """Dibuja los tres botones de habilidad con su estado actual."""
    rects = get_barra_rects()
    restantes = max(0, Config.MAX_SKILL_USES_PER_LEVEL - sistema.usos_nivel)
    encabezado = texto(font_small, f"Habilidades  ·  usos restantes en el nivel: {restantes}", (92, 52, 36))
    primer = rects[HABILIDADES[0]['id']]
    ventana.blit(encabezado, (primer.x, primer.y - 22))

    for h in HABILIDADES:
        hid = h['id']
        rect = rects[hid]
        estado = sistema.estado_de(hid)

        if estado == 'limite':
            base, etiqueta = (150, 140, 135), "Límite"
        elif estado == 'enfriando':
            base, etiqueta = (128, 128, 140), f"{int(sistema.segundos_restantes(hid)) + 1}s"
        elif estado == 'lista':
            base, etiqueta = h['color'], "¡Lista!"
        else:
            base, etiqueta = tuple(int(c * 0.55) for c in h['color']), "Responder"

        superficie = _superficie_boton(h, tuple(base), etiqueta, seleccionada == hid,
                                       rect.collidepoint(mouse_pos), rect.size)
        ventana.blit(superficie, rect.topleft)

    return rects


# -------------------- MODAL DE PREGUNTA --------------------
async def preguntar_para_habilidad(ventana, tablero, hid, sound=None, tema_id='matrices'):
    """Pregunta para ganar la habilidad. Devuelve (acertó, segundos_de_pausa)."""
    habilidad = _POR_ID[hid]
    pregunta = pick_question(tablero, tema_id)
    entrada = time.time()
    clock = pygame.time.Clock()

    ancho, alto = 760, 460
    rect = pygame.Rect((Config.ANCHO - ancho) // 2, (Config.ALTO - alto) // 2, ancho, alto)
    fase = 'pregunta'
    elegida = None

    while True:
        mouse_pos = entrada.posicion_puntero()
        opciones_rects = []

        capa = pygame.Surface((Config.ANCHO, Config.ALTO), pygame.SRCALPHA)
        capa.fill((10, 10, 10, 195))
        ventana.blit(capa, (0, 0))

        pygame.draw.rect(ventana, (250, 248, 252), rect, border_radius=18)
        pygame.draw.rect(ventana, habilidad['color'], rect, 5, border_radius=18)

        icono = _icono(hid, 54)
        ventana.blit(icono, icono.get_rect(center=(rect.x + 52, rect.y + 48)))
        ventana.blit(texto(font_large, f"Habilidad: {habilidad['nombre']}", habilidad['color']), (rect.x + 92, rect.y + 26))
        ventana.blit(texto(font_small, habilidad['desc'], (70, 60, 60)), (rect.x + 92, rect.y + 60))
        ventana.blit(texto(font_small, "Responde correctamente para cargarla.", (120, 90, 60)), (rect.x + 28, rect.y + 96))

        y = rect.y + 128
        for linea in pregunta['lines']:
            ventana.blit(texto(font_large, linea, (25, 25, 30)), (rect.x + 28, y))
            y += 32

        y += 12
        for idx, opcion in enumerate(pregunta['options']):
            opt_rect = pygame.Rect(rect.x + 40, y, rect.width - 80, 46)
            opciones_rects.append(opt_rect)
            base, hov = (232, 228, 242), (216, 212, 236)
            if fase == 'feedback':
                if idx == pregunta['correct_idx']:
                    base = hov = (168, 220, 168)
                elif idx == elegida:
                    base = hov = (232, 158, 158)
            draw_button(ventana, opt_rect, opcion, mouse_pos, base, hov, text_color=(25, 25, 30))
            y += 54

        boton_cerrar = None
        if fase == 'feedback':
            acierto = elegida == pregunta['correct_idx']
            msg = f"¡Correcto! {habilidad['nombre']} cargada." if acierto else "Incorrecto. La habilidad no se carga."
            ventana.blit(texto(font_large, msg, (30, 130, 45) if acierto else (170, 45, 45)), (rect.x + 28, y + 4))
            yy = y + 40
            for linea in _envolver(pregunta.get('explanation', ''), 68):
                ventana.blit(texto(font_small, linea, (60, 60, 60)), (rect.x + 28, yy))
                yy += 21
            boton_cerrar = pygame.Rect(rect.right - 180, rect.bottom - 60, 150, 44)
            draw_button(ventana, boton_cerrar, "Continuar", mouse_pos, (70, 150, 95), (95, 180, 120))

        pygame.display.flip()
        clock.tick(30)
        await asyncio.sleep(0)

        for ev in entrada.obtener_eventos():
            if ev.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE and fase == 'pregunta':
                return False, time.time() - entrada
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if fase == 'pregunta':
                    for idx, opt_rect in enumerate(opciones_rects):
                        if opt_rect.collidepoint(ev.pos):
                            elegida = idx
                            fase = 'feedback'
                            if sound:
                                sound.play('correct' if idx == pregunta['correct_idx'] else 'error')
                elif boton_cerrar and boton_cerrar.collidepoint(ev.pos):
                    return elegida == pregunta['correct_idx'], time.time() - entrada


def _envolver(texto_largo, max_len=68):
    if not texto_largo:
        return []
    palabras = texto_largo.split()
    lineas, actual = [], palabras[0]
    for palabra in palabras[1:]:
        if len(actual + ' ' + palabra) <= max_len:
            actual += ' ' + palabra
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas
