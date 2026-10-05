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

from config import Config, BLANCO, font, font_small
from ui import draw_button, texto
from fuentes import fuente, TITULO_SUAVE, TEXTO, TEXTO_FUERTE
from luces import multiplicar_todo
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
    """Pregunta para ganar una habilidad de Matrices. Devuelve (acertó, pausa)."""
    return await modal_pregunta(ventana, _POR_ID[hid], _icono(hid, 56),
                                pick_question(tablero, tema_id), sound)


def _envolver_px(fuente_txt, texto_largo, ancho_max):
    """Parte un texto en líneas que caben en `ancho_max` píxeles. Por caracteres
    (como antes) no sirve: el ancho real depende de la fuente y de las letras."""
    palabras = texto_largo.split()
    if not palabras:
        return []
    lineas, actual = [], palabras[0]
    for palabra in palabras[1:]:
        candidato = actual + ' ' + palabra
        if fuente_txt.size(candidato)[0] <= ancho_max:
            actual = candidato
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def _aclarar(color, k):
    return tuple(int(c + (255 - c) * k) for c in color)


async def modal_pregunta(ventana, habilidad, icono, pregunta, sound=None):
    """Ventana de pregunta para cargar una habilidad, común a los tres minijuegos.

    Antes cada minijuego tenía su propia copia, casi idéntica, con un alto fijo:
    la explicación se salía por debajo del recuadro, y en Vectores y Sistemas ni
    siquiera se mostraba, así que el estudiante no veía por qué había acertado o
    fallado. Ahora el alto se calcula a partir del contenido y la explicación
    aparece siempre. Devuelve (acertó, segundos que estuvo abierta).
    """
    clock = pygame.time.Clock()
    inicio = time.time()

    # La partida queda detrás, congelada y oscurecida una sola vez (antes se
    # creaba una capa de pantalla completa con alfa en cada fotograma).
    fondo = ventana.copy()
    multiplicar_todo(fondo, (96, 78, 92))

    f_titulo = fuente(TITULO_SUAVE, 30)
    f_desc = fuente(TEXTO, 16)
    f_preg = fuente(TITULO_SUAVE, 27)
    f_opcion = fuente(TEXTO_FUERTE, 19)
    f_msg = fuente(TITULO_SUAVE, 25)
    f_expl = fuente(TEXTO, 16)
    f_num = fuente(TEXTO_FUERTE, 15)
    f_boton = fuente(TITULO_SUAVE, 22)

    ancho = 800
    pad = 34
    interior = ancho - 2 * pad
    color = habilidad['color']
    oscuro = tuple(int(c * 0.62) for c in color)

    desc = _envolver_px(f_desc, habilidad['desc'], interior - 84)
    preg = _envolver_px(f_preg, " ".join(pregunta['lines']), interior)
    expl = _envolver_px(f_expl, pregunta.get('explanation', ''), interior)
    n_op = len(pregunta['options'])

    # ---- maqueta vertical (distancias desde el borde superior de la tarjeta)
    alto_cabecera = 30 + 34 + 20 * len(desc) + 18
    y_instr = alto_cabecera + 16
    y_preg = y_instr + 26
    y_ops = y_preg + 34 * len(preg) + 14
    alto_op, sep_op = 50, 10
    fin_ops = y_ops + n_op * (alto_op + sep_op) - sep_op
    alto_pregunta = fin_ops + pad
    y_msg = fin_ops + 20
    y_expl = y_msg + 38
    y_boton = y_expl + 22 * len(expl) + (14 if expl else 0)
    alto_total = y_boton + 50 + pad

    x0 = (Config.ANCHO - ancho) // 2
    # Se centra según el alto final (con la explicación): así la tarjeta no
    # salta al responder, solo crece hacia abajo.
    y0 = max(16, (Config.ALTO - alto_total) // 2)

    fase = 'pregunta'
    elegida = None
    t_respuesta = None

    while True:
        ahora = time.time()
        mouse_pos = entrada.posicion_puntero()
        k_feed = 0.0 if t_respuesta is None else min(1.0, (ahora - t_respuesta) / 0.22)
        k_feed = 1 - (1 - k_feed) ** 3
        alto = int(alto_pregunta + (alto_total - alto_pregunta) * k_feed)
        tarjeta = pygame.Rect(x0, y0, ancho, alto)

        ventana.blit(fondo, (0, 0))
        pygame.draw.rect(ventana, (26, 16, 28), tarjeta.move(0, 8), border_radius=22)
        pygame.draw.rect(ventana, (252, 249, 246), tarjeta, border_radius=22)
        cabecera = pygame.Rect(x0, y0, ancho, alto_cabecera)
        pygame.draw.rect(ventana, _aclarar(color, 0.82), cabecera,
                         border_top_left_radius=22, border_top_right_radius=22)
        pygame.draw.rect(ventana, color, tarjeta, 4, border_radius=22)

        # Cabecera: icono, nombre de la habilidad y qué hace
        centro_icono = (x0 + pad + 30, y0 + alto_cabecera // 2)
        pygame.draw.circle(ventana, (255, 255, 255), centro_icono, 36)
        pygame.draw.circle(ventana, color, centro_icono, 36, 3)
        ventana.blit(icono, icono.get_rect(center=centro_icono))
        tx = x0 + pad + 84
        ventana.blit(texto(f_titulo, "Habilidad: " + habilidad['nombre'], oscuro), (tx, y0 + 24))
        for i, linea in enumerate(desc):
            ventana.blit(texto(f_desc, linea, (88, 66, 66)), (tx, y0 + 62 + 20 * i))

        ventana.blit(texto(f_desc, "Responde bien para cargarla", (150, 112, 92)),
                     (x0 + pad, y0 + y_instr))
        for i, linea in enumerate(preg):
            ventana.blit(texto(f_preg, linea, (42, 28, 32)), (x0 + pad, y0 + y_preg + 34 * i))

        opciones_rects = []
        for idx, opcion in enumerate(pregunta['options']):
            r = pygame.Rect(x0 + pad, y0 + y_ops + idx * (alto_op + sep_op), interior, alto_op)
            opciones_rects.append(r)
            base, hov, borde = (241, 236, 248), (228, 220, 246), (206, 196, 222)
            if fase == 'feedback':
                if idx == pregunta['correct_idx']:
                    base = hov = (178, 226, 178)
                    borde = (70, 160, 90)
                elif idx == elegida:
                    base = hov = (242, 170, 166)
                    borde = (196, 72, 66)
                else:
                    base = hov = borde = (238, 236, 240)
            encima = fase == 'pregunta' and r.collidepoint(mouse_pos)
            pygame.draw.rect(ventana, hov if encima else base, r, border_radius=14)
            pygame.draw.rect(ventana, borde, r, 2, border_radius=14)
            # Insignia con la tecla (1, 2, 3...) para responder con el teclado
            cx_ins = (r.x + 30, r.centery)
            pygame.draw.circle(ventana, (255, 255, 255), cx_ins, 15)
            pygame.draw.circle(ventana, borde, cx_ins, 15, 2)
            num = texto(f_num, str(idx + 1), (90, 70, 96))
            ventana.blit(num, num.get_rect(center=cx_ins))
            etq = texto(f_opcion, opcion, (36, 26, 34))
            ventana.blit(etq, etq.get_rect(center=(r.centerx + 15, r.centery)))

        boton_cerrar = None
        if fase == 'feedback' and k_feed > 0.6:
            acierto = elegida == pregunta['correct_idx']
            if acierto:
                msg, col_msg = "¡Correcto! %s cargada." % habilidad['nombre'], (38, 140, 62)
            else:
                msg, col_msg = "Incorrecto: la habilidad no se carga.", (190, 52, 52)
            ventana.blit(texto(f_msg, msg, col_msg), (x0 + pad, y0 + y_msg))
            for i, linea in enumerate(expl):
                ventana.blit(texto(f_expl, linea, (72, 62, 64)), (x0 + pad, y0 + y_expl + 22 * i))
            boton_cerrar = pygame.Rect(x0 + ancho - pad - 200, y0 + y_boton, 200, 50)
            draw_button(ventana, boton_cerrar, "Continuar", mouse_pos, (64, 150, 92), (88, 178, 116),
                        font_obj=f_boton)

        pygame.display.flip()
        clock.tick(30)
        await asyncio.sleep(0)

        for ev in entrada.obtener_eventos():
            if ev.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if time.time() - inicio < 0.25:
                continue  # el clic que abrió la ventana no debe elegir una respuesta
            if fase == 'pregunta':
                eleccion = None
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    return False, time.time() - inicio
                if ev.type == pygame.KEYDOWN and pygame.K_1 <= ev.key < pygame.K_1 + n_op:
                    eleccion = ev.key - pygame.K_1
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    for idx, r in enumerate(opciones_rects):
                        if r.collidepoint(ev.pos):
                            eleccion = idx
                if eleccion is not None:
                    elegida = eleccion
                    fase = 'feedback'
                    t_respuesta = time.time()
                    if sound:
                        sound.play('correct' if eleccion == pregunta['correct_idx'] else 'error')
            elif boton_cerrar is not None:
                tecla = ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                                 pygame.K_SPACE)
                clic = ev.type == pygame.MOUSEBUTTONDOWN and boton_cerrar.collidepoint(ev.pos)
                if tecla or clic:
                    return elegida == pregunta['correct_idx'], time.time() - inicio


