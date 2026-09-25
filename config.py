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
def create_font(size, bold=False):
    """Crea una fuente segura con fallback en caso de error."""
    try:
        return pygame.font.SysFont('arial', size, bold=bold)
    except:
        return pygame.font.Font(None, size)

# Fuentes globales
font_small = create_font(16)
font = create_font(20)
font_large = create_font(30, bold=True)
font_title = create_font(48, bold=True)

# ------------------- UTILIDADES -------------------
def draw_text_center(surface, text, font, color, y_offset=0):
    """Dibuja texto centrado horizontalmente."""
    text_surface = font.render(text, True, color)
    rect = text_surface.get_rect(center=(Config.ANCHO // 2, Config.ALTO // 2 + y_offset))
    surface.blit(text_surface, rect)
