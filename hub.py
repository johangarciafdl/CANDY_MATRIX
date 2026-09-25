# hub.py
"""Hub de selección de tema: se muestra entre el menú principal y la partida.

Cada tarjeta es un tema de álgebra lineal. Los disponibles se pueden jugar ya
mismo; los "Próximamente" quedan visibles para dejar claro el roadmap del
proyecto sin bloquear al jugador con un menú vacío."""
import sys
import pygame

from config import Config, font, font_small, font_large, font_title
from ui import draw_button, texto, get_fondo_menu
from topics import TEMAS
import progress


def mostrar_hub_temas(ventana, tema_actual='matrices'):
    """Devuelve el id del tema elegido, o None si el jugador pulsó 'Volver'."""
    clock = pygame.time.Clock()
    fondo = get_fondo_menu()

    cols = 3
    card_w, card_h = 320, 190
    gap_x, gap_y = 30, 26
    total_w = cols * card_w + (cols - 1) * gap_x
    x0 = (Config.ANCHO - total_w) // 2
    y0 = 250

    rects = {}
    for idx, t in enumerate(TEMAS):
        fila, col = divmod(idx, cols)
        x = x0 + col * (card_w + gap_x)
        y = y0 + fila * (card_h + gap_y)
        rects[t['id']] = pygame.Rect(x, y, card_w, card_h)

    btn_volver = pygame.Rect(40, Config.ALTO - 76, 160, 50)

    while True:
        ventana.blit(fondo, (0, 0))
        titulo = font_title.render("Elige un tema", True, (206, 42, 62))
        ventana.blit(titulo, titulo.get_rect(center=(Config.ANCHO // 2, 110)))
        sub = font.render("Cada tema tiene su propio tablero, preguntas y Zona de Estudio.", True, (86, 34, 24))
        ventana.blit(sub, sub.get_rect(center=(Config.ANCHO // 2, 158)))

        mouse_pos = pygame.mouse.get_pos()

        for t in TEMAS:
            rect = rects[t['id']]
            hovered = rect.collidepoint(mouse_pos)
            base = t['color'] if t['disponible'] else (172, 166, 160)
            color_fondo = tuple(min(255, int(c * 1.15)) for c in base) if (hovered and t['disponible']) else base

            pygame.draw.rect(ventana, tuple(int(c * 0.5) for c in color_fondo), rect.move(0, 5), border_radius=18)
            pygame.draw.rect(ventana, color_fondo, rect, border_radius=18)
            borde = (255, 226, 90) if t['id'] == tema_actual else (255, 255, 255)
            pygame.draw.rect(ventana, borde, rect, 3, border_radius=18)

            ventana.blit(texto(font_large, t['nombre'], (255, 255, 255)), (rect.x + 18, rect.y + 16))
            for i, linea in enumerate(_envolver(t['resumen'], 30)):
                ventana.blit(texto(font_small, linea, (255, 255, 255)), (rect.x + 18, rect.y + 56 + i * 20))

            if t['disponible']:
                prog = progress.resumen(t['id'])
                estado = (f"Mejor: Nivel {prog['mejor_nivel']} · {prog['mejor_puntaje']} pts"
                          if prog['mejor_nivel'] > 0 else "Aún sin jugar")
            else:
                estado = "Próximamente"
            ventana.blit(texto(font_small, estado, (255, 245, 225)), (rect.x + 18, rect.bottom - 30))

        draw_button(ventana, btn_volver, "Volver", mouse_pos, (150, 90, 70), (180, 115, 90), font_obj=font_small)

        pygame.display.flip()
        clock.tick(Config.FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_volver.collidepoint(event.pos):
                    return None
                for t in TEMAS:
                    if t['disponible'] and rects[t['id']].collidepoint(event.pos):
                        return t['id']


def _envolver(texto_largo, max_len=30):
    palabras = texto_largo.split()
    if not palabras:
        return []
    lineas, actual = [], palabras[0]
    for palabra in palabras[1:]:
        if len(actual + ' ' + palabra) <= max_len:
            actual += ' ' + palabra
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas
