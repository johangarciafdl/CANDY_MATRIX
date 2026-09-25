import pygame, pygame.gfxdraw, sys, math
from config import Config, COLOR_MAP, BLANCO, font, font_small, font_large, font_title
from fruits import get_fruit_sprite


# -------------------- PRIMITIVAS CON ANTIALIASING --------------------
# pygame.draw.circle deja bordes dentados a los tamaños pequeños que usa este
# juego; gfxdraw sí puede suavizarlos, así que estas dos funciones son el
# reemplazo estándar en toda la interfaz.
def draw_circle_aa(surface, center, radio, color):
    """Círculo relleno con antialiasing."""
    x, y = int(center[0]), int(center[1])
    r = max(1, int(radio))
    pygame.gfxdraw.filled_circle(surface, x, y, r, color)
    pygame.gfxdraw.aacircle(surface, x, y, r, color)


def draw_ring_aa(surface, center, radio, grosor, color):
    """Anillo (círculo hueco) con antialiasing, apilando aros de 1px."""
    x, y = int(center[0]), int(center[1])
    for i in range(max(1, int(grosor))):
        pygame.gfxdraw.aacircle(surface, x, y, max(1, int(radio) + i), color)

# -------------------- FUNCIONES DE ANIMACIÓN --------------------
def fade_in(surface, color=(0, 0, 0), duration=500):
    """Efecto de aparición (fade in) suave."""
    fade = pygame.Surface((Config.ANCHO, Config.ALTO))
    fade.fill(color)
    for alpha in range(255, -1, -15):
        fade.set_alpha(alpha)
        surface.blit(fade, (0, 0))
        pygame.display.flip()
        pygame.time.delay(duration // 18)


def lighten(color, factor=0.6):
    """Devuelve una versión más clara (pastel) de un color, hacia el blanco."""
    return tuple(int(c + (255 - c) * factor) for c in color)


def darken(color, factor=0.35):
    """Devuelve una versión más oscura de un color."""
    return tuple(int(c * (1 - factor)) for c in color)


# -------------------- FONDOS HORNEADOS (se rasterizan una sola vez) --------------------
_FONDO_MENU = None
_FONDO_JUEGO = None
_DIGITOS = {}


def _degradado_vertical(ancho, alto, color_arriba, color_abajo):
    superficie = pygame.Surface((ancho, alto))
    for y in range(alto):
        k = y / max(1, alto - 1)
        color = tuple(int(a + (b - a) * k) for a, b in zip(color_arriba, color_abajo))
        pygame.draw.line(superficie, color, (0, y), (ancho, y))
    return superficie


def get_fondo_menu():
    global _FONDO_MENU
    if _FONDO_MENU is None:
        _FONDO_MENU = _degradado_vertical(Config.ANCHO, Config.ALTO, (255, 232, 208), (243, 190, 160))
    return _FONDO_MENU


def get_fondo_juego():
    """Fondo del área de juego con el marco y el cuadriculado del tablero ya dibujados."""
    global _FONDO_JUEGO
    if _FONDO_JUEGO is None:
        s = _degradado_vertical(Config.LEFT_WIDTH, Config.ALTO, (247, 218, 190), (231, 190, 158))
        ancho = Config.COLUMNAS * Config.TAMANO_CELDA
        alto = Config.FILAS * Config.TAMANO_CELDA
        marco = pygame.Rect(Config.MARGEN_IZQUIERDO - 14, Config.MARGEN_SUPERIOR - 14, ancho + 28, alto + 28)

        pygame.draw.rect(s, (150, 100, 62), marco.move(0, 5), border_radius=20)
        pygame.draw.rect(s, (196, 140, 96), marco, border_radius=20)
        pygame.draw.rect(s, (120, 78, 45), marco, 4, border_radius=20)

        for i in range(Config.FILAS):
            for j in range(Config.COLUMNAS):
                color = (240, 219, 193) if (i + j) % 2 == 0 else (228, 202, 174)
                celda = pygame.Rect(Config.MARGEN_IZQUIERDO + j * Config.TAMANO_CELDA,
                                    Config.MARGEN_SUPERIOR + i * Config.TAMANO_CELDA,
                                    Config.TAMANO_CELDA, Config.TAMANO_CELDA)
                pygame.draw.rect(s, color, celda)
        _FONDO_JUEGO = s
    return _FONDO_JUEGO


def get_area_tablero():
    """Rect del tablero, usado para recortar las frutas que caen desde arriba."""
    return pygame.Rect(Config.MARGEN_IZQUIERDO, Config.MARGEN_SUPERIOR,
                       Config.COLUMNAS * Config.TAMANO_CELDA, Config.FILAS * Config.TAMANO_CELDA)


def _digito(valor):
    if valor not in _DIGITOS:
        _DIGITOS[valor] = font_small.render(str(valor), True, (40, 25, 15))
    return _DIGITOS[valor]


_TEXTOS = {}
_GLOSS = {}


def texto(fuente, cadena, color):
    """Cachea superficies de texto: rasterizar la misma cadena 60 veces por segundo
    era el segundo gasto más grande del frame."""
    clave = (id(fuente), cadena, color)
    superficie = _TEXTOS.get(clave)
    if superficie is None:
        if len(_TEXTOS) > 400:
            _TEXTOS.clear()
        superficie = fuente.render(cadena, True, color)
        _TEXTOS[clave] = superficie
    return superficie


def _gloss(ancho, alto, radio):
    clave = (ancho, alto, radio)
    superficie = _GLOSS.get(clave)
    if superficie is None:
        superficie = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        pygame.draw.rect(superficie, (255, 255, 255, 80), superficie.get_rect(), border_radius=radio)
        _GLOSS[clave] = superficie
    return superficie


# -------------------- BOTONES REUTILIZABLES (estilo candy/glossy) --------------------
def draw_button(surface, rect, text, mouse_pos, base_color=(210, 100, 80),
                 hover_color=(250, 140, 110), text_color=BLANCO, font_obj=None, radius=14):
    """Dibuja un botón grueso, redondeado y con brillo superior (glossy)."""
    font_obj = font_obj or font
    hovered = rect.collidepoint(mouse_pos)
    color = hover_color if hovered else base_color
    draw_rect = rect.inflate(6, 6) if hovered else rect

    pygame.draw.rect(surface, darken(color, 0.55), draw_rect.move(0, 4), border_radius=radius)
    pygame.draw.rect(surface, color, draw_rect, border_radius=radius)

    gloss_h = max(4, draw_rect.height // 2 - 2)
    surface.blit(_gloss(max(1, draw_rect.width - 10), gloss_h, max(2, radius - 4)),
                 (draw_rect.x + 5, draw_rect.y + 3))

    pygame.draw.rect(surface, BLANCO, draw_rect, 3, border_radius=radius)
    text_surface = texto(font_obj, text, text_color)
    surface.blit(text_surface, text_surface.get_rect(center=draw_rect.center))
    return hovered


def draw_progress_bar(surface, rect, ratio, fill_color, bg_color=(235, 225, 215), border_radius=8):
    """Barra de progreso genérica. ratio entre 0 y 1."""
    ratio = max(0.0, min(1.0, ratio))
    pygame.draw.rect(surface, bg_color, rect, border_radius=border_radius)
    fill_rect = pygame.Rect(rect.x, rect.y, int(rect.width * ratio), rect.height)
    if fill_rect.width > 0:
        pygame.draw.rect(surface, fill_color, fill_rect, border_radius=border_radius)
    pygame.draw.rect(surface, (110, 90, 80), rect, 2, border_radius=border_radius)


def draw_seleccion(surface, center, radio):
    """Aro dorado pulsante sobre la fruta seleccionada."""
    x, y = center
    pulso = 4 + int(3 * math.sin(pygame.time.get_ticks() / 120))
    draw_ring_aa(surface, (x, y), radio + 8 + pulso, 4, (255, 255, 255))
    draw_ring_aa(surface, (x, y), radio + 4 + pulso, 3, (255, 210, 40))


# -------------------- TABLA DE MATRIZ EN VIVO --------------------
_TABLA = {'clave': None, 'superficie': None}


def _render_matrix_table(tamano, tablero, changed_cells):
    ancho, alto = tamano
    filas = len(tablero)
    columnas = len(tablero[0]) if filas else 0
    s = pygame.Surface(tamano, pygame.SRCALPHA)
    cell_w = ancho / columnas
    cell_h = alto / filas

    for i in range(filas):
        for j in range(columnas):
            valor = tablero[i][j]
            cell_rect = pygame.Rect(int(j * cell_w), int(i * cell_h), int(cell_w) - 2, int(cell_h) - 2)

            es_cambio = (i, j) in changed_cells
            valido = isinstance(valor, int) and 0 <= valor < len(COLOR_MAP)
            base_color = COLOR_MAP[valor] if valido else (200, 200, 200)
            fondo = (255, 236, 150) if es_cambio else lighten(base_color, 0.72)

            pygame.draw.rect(s, fondo, cell_rect, border_radius=5)
            borde = (235, 160, 20) if es_cambio else darken(base_color, 0.2)
            pygame.draw.rect(s, borde, cell_rect, 2 if es_cambio else 1, border_radius=5)

            if valido:
                digito = _digito(valor)
                s.blit(digito, digito.get_rect(center=cell_rect.center))
    return s


def draw_matrix_table(surface, area_rect, tablero, changed_cells=None):
    """Dibuja la matriz numérica exacta del tablero y resalta en dorado las celdas
    que cambiaron en el último movimiento. La tabla se rasteriza solo cuando el
    tablero cambia; el resto de los frames es un único blit."""
    changed_cells = changed_cells or set()
    if not tablero or not tablero[0]:
        return

    clave = (tuple(tuple(fila) for fila in tablero), frozenset(changed_cells), area_rect.size)
    if _TABLA['clave'] != clave:
        _TABLA['superficie'] = _render_matrix_table(area_rect.size, tablero, changed_cells)
        _TABLA['clave'] = clave
    surface.blit(_TABLA['superficie'], area_rect.topleft)


# -------------------- MENÚ PRINCIPAL --------------------
# Posiciones decorativas: deliberadamente fuera de la columna central, para que
# ninguna fruta se cruce con el título, el subtítulo ni los botones.
_DECOR_MENU = [
    (120, 150), (205, 335), (108, 515), (235, 655),
    (1080, 150), (995, 335), (1092, 515), (965, 655),
    (470, 62), (725, 55), (600, 48),
    (505, 700), (700, 712),
]


def mostrar_menu_inicio(ventana):
    """Pantalla de inicio: fondo horneado, frutas flotando y botones sin solapes."""
    clock = pygame.time.Clock()
    fondo = get_fondo_menu()

    ventana.blit(fondo, (0, 0))
    pygame.display.flip()
    fade_in(ventana, (250, 214, 185))

    botones = {
        "comenzar": pygame.Rect(Config.ANCHO // 2 - 140, 300, 280, 62),
        "estudio": pygame.Rect(Config.ANCHO // 2 - 140, 382, 280, 62),
        "salir": pygame.Rect(Config.ANCHO // 2 - 140, 464, 280, 62),
    }
    etiquetas = {
        "comenzar": "Comenzar Juego",
        "estudio": "Zona de Estudio",
        "salir": "Salir",
    }

    pygame.mixer.music.set_volume(0.2)

    while True:
        ventana.blit(fondo, (0, 0))
        t = pygame.time.get_ticks() / 700.0

        for indice, (dx, dy) in enumerate(_DECOR_MENU):
            tipo = indice % len(COLOR_MAP)
            sprite = get_fruit_sprite(tipo, 26)
            y = dy + 10 * math.sin(t + indice * 0.7)
            ventana.blit(sprite, sprite.get_rect(center=(dx, int(y))))

        titulo = font_title.render("CANDY MATRIX", True, (206, 42, 62))
        sombra = font_title.render("CANDY MATRIX", True, (112, 16, 28))
        ventana.blit(sombra, sombra.get_rect(center=(Config.ANCHO // 2 + 3, 153)))
        ventana.blit(titulo, titulo.get_rect(center=(Config.ANCHO // 2, 150)))

        subtitulo = font.render("Aprende matrices jugando: álgebra lineal en modo Match-3", True, (86, 34, 24))
        ventana.blit(subtitulo, subtitulo.get_rect(center=(Config.ANCHO // 2, 215)))

        mouse_pos = pygame.mouse.get_pos()
        for nombre, rect in botones.items():
            draw_button(ventana, rect, etiquetas[nombre], mouse_pos, (233, 90, 64), (247, 130, 95), font_obj=font_large)

        ayuda = font_small.render("Intercambia frutas vecinas para alinear 3 o más. ESC abre la Zona de Estudio.",
                                  True, (112, 68, 56))
        ventana.blit(ayuda, ayuda.get_rect(center=(Config.ANCHO // 2, 570)))

        pygame.display.flip()
        clock.tick(Config.FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if botones["comenzar"].collidepoint(event.pos):
                    return "comenzar"
                elif botones["estudio"].collidepoint(event.pos):
                    return "estudio"
                elif botones["salir"].collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()


# -------------------- PANEL DERECHO --------------------
def get_panel_buttons():
    """Rects de los botones del panel derecho (sin dibujar), para hit-testing."""
    panel_x = Config.LEFT_WIDTH
    return {
        "estudio": pygame.Rect(panel_x + 30, 592, Config.RIGHT_PANEL_WIDTH - 60, 55),
        "excel": pygame.Rect(panel_x + 30, 657, Config.RIGHT_PANEL_WIDTH - 60, 55),
    }


def get_matrix_table_rect():
    panel_x = Config.LEFT_WIDTH
    size = 286
    x = panel_x + (Config.RIGHT_PANEL_WIDTH - size) // 2
    return pygame.Rect(x, 86, size, size)


def draw_right_panel(ventana, level, score, moves, tiempo_restante, goal=None, tablero=None,
                     changed_cells=None, tema_nombre=None, mostrar_matriz=True):
    """Panel lateral: nivel, MATRIZ EN VIVO del tablero (opcional), puntuación/meta,
    tiempo y botones. mostrar_matriz=False lo usan los minijuegos sin tablero de
    celdas (por ejemplo Vectores), que dibujan su propia visualización a la izquierda."""
    panel_x = Config.LEFT_WIDTH
    mouse_pos = pygame.mouse.get_pos()
    pygame.draw.rect(ventana, (255, 245, 235), (panel_x, 0, Config.RIGHT_PANEL_WIDTH, Config.ALTO))
    pygame.draw.line(ventana, (215, 150, 120), (panel_x, 0), (panel_x, Config.ALTO), 4)

    if tema_nombre:
        ventana.blit(texto(font_small, tema_nombre, (150, 90, 40)), (panel_x + 30, 4))
    ventana.blit(texto(font_large, f"Nivel {level}", (140, 30, 30)), (panel_x + 30, 26))

    if mostrar_matriz:
        ventana.blit(texto(font_small, "Matriz del tablero (en vivo)", (60, 30, 20)), (panel_x + 30, 64))
        tabla_rect = get_matrix_table_rect()
        if tablero is not None:
            draw_matrix_table(ventana, tabla_rect, tablero, changed_cells)
        if changed_cells:
            ventana.blit(texto(font_small, "Dorado = celdas que cambiaron", (150, 110, 20)),
                         (panel_x + 30, tabla_rect.bottom + 4))

    card = pygame.Rect(panel_x + 25, 400, Config.RIGHT_PANEL_WIDTH - 50, 100)
    pygame.draw.rect(ventana, (255, 255, 255), card, border_radius=14)
    pygame.draw.rect(ventana, (220, 190, 170), card, 2, border_radius=14)

    ventana.blit(texto(font, f"Puntuación: {score}", (50, 20, 20)), (card.x + 15, card.y + 8))
    ventana.blit(texto(font, f"Movimientos: {moves}", (50, 20, 20)), (card.x + 15, card.y + 34))

    if goal:
        ratio = min(1.0, score / goal) if goal else 0
        ventana.blit(texto(font_small, f"Meta: {score}/{goal} pts", (50, 20, 20)), (card.x + 15, card.y + 62))
        draw_progress_bar(ventana, pygame.Rect(card.x + 15, card.y + 82, card.width - 30, 14), ratio, (90, 190, 110))

    time_ratio = max(0.0, min(1.0, tiempo_restante / Config.LEVEL_TIME))
    time_color = (90, 170, 220) if time_ratio > 0.3 else (220, 90, 70)
    ventana.blit(texto(font, f"Tiempo: {int(tiempo_restante)}s", (50, 20, 20)), (panel_x + 30, 514))
    draw_progress_bar(ventana, pygame.Rect(panel_x + 30, 542, Config.RIGHT_PANEL_WIDTH - 60, 18), time_ratio, time_color)

    botones = get_panel_buttons()
    draw_button(ventana, botones["estudio"], "Zona de Estudio", mouse_pos, (200, 100, 60), (230, 130, 85))
    draw_button(ventana, botones["excel"], "Exportar Excel", mouse_pos, (60, 130, 210), (90, 160, 235))

    ventana.blit(texto(font_small, "ESC: Zona de Estudio", (130, 90, 80)), (panel_x + 30, 722))
    return botones
