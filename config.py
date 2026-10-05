import pygame

# Inicializa pygame y el módulo de fuentes
pygame.init()
pygame.font.init()

# ------------------- CONFIGURACIÓN GENERAL -------------------
class Config:
    ANCHO = 1200
    ALTO = 800

    FILAS = 8
    COLUMNAS = 8
    TAMANO_CELDA = 64

    RIGHT_PANEL_WIDTH = 360
    LEFT_WIDTH = ANCHO - RIGHT_PANEL_WIDTH

    MARGEN_SUPERIOR = (ALTO - (FILAS * TAMANO_CELDA)) // 2
    MARGEN_IZQUIERDO = (LEFT_WIDTH - (COLUMNAS * TAMANO_CELDA)) // 2

    LEVEL_TIME = 180
    MAX_LEVEL = 5
    GOAL_BASE = 500
    MAX_SKILL_USES_PER_LEVEL = 4

    FPS = 60
    RADIO_FRUTA = TAMANO_CELDA // 2 - 10

# ------------------- COLORES -------------------
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
GRIS = (200, 200, 200)
CAFE_CLARO = (195, 155, 110)
CAFE_OSCURO = (120, 80, 40)
NARANJA = (255, 165, 0)
AZUL_SUAVE = (150, 200, 255)
VERDE_SUAVE = (170, 255, 170)

COLOR_MAP = [
    (230, 57, 70),   # 0 Manzana
    (124, 190, 60),  # 1 Pera
    (72, 118, 214),  # 2 Arándano
    (247, 203, 60),  # 3 Limón
    (155, 89, 182),  # 4 Uva
    (247, 147, 40),  # 5 Naranja
    (233, 90, 130),  # 6 Sandía
]

FRUTAS = ["Manzana", "Pera", "Arándano", "Limón", "Uva", "Naranja", "Sandía"]

# ------------------- FUENTES -------------------
# Fuentes incluidas en assets/fonts (ver fuentes.py): en el navegador no hay
# fuentes del sistema, así que con SysFont('arial') la web se veía distinta.
#
# Los tamaños no son los mismos que tenía Arial porque Nunito es más ancha: a
# igual tamaño ocupa ~22 % más. Se eligieron para conservar la altura de las
# minúsculas (lo que decide si se lee bien) sin ensanchar más de un 10 %, que
# los diseños existentes absorben. Fredoka es más estrecha que Arial negrita,
# por eso los títulos sí pudieron crecer.
from fuentes import fuente, TITULO, TITULO_SUAVE, TEXTO, TEXTO_FUERTE

font_small = fuente(TEXTO, 14)
font = fuente(TEXTO, 17)
font_large = fuente(TITULO_SUAVE, 30)
font_title = fuente(TITULO, 50)


def create_font(size, bold=False):
    """Compatibilidad: fuente de texto (o de título si bold) a un tamaño dado."""
    return fuente(TITULO_SUAVE if bold else TEXTO, size)

# ------------------- UTILIDADES -------------------
def draw_text_center(surface, text, font, color, y_offset=0):
    """Dibuja texto centrado horizontalmente."""
    text_surface = font.render(text, True, color)
    rect = text_surface.get_rect(center=(Config.ANCHO // 2, Config.ALTO // 2 + y_offset))
    surface.blit(text_surface, rect)
