# hub.py
"""Hub de selección de tema: se muestra entre el menú principal y la partida.

Cada tarjeta es un tema de álgebra lineal. Los disponibles se pueden jugar ya
mismo; los "Próximamente" quedan visibles para dejar claro el roadmap del
proyecto, pero avisan al pulsarlos en vez de no hacer nada (eso se sentía
como un botón roto)."""
import asyncio
import time
import sys
import pygame

from config import Config, font, font_small, font_large, font_title
from ui import draw_button, texto, get_fondo_menu
from topics import TEMAS
import progress

DUR_AVISO = 2.4


async def mostrar_hub_temas(ventana, estudiante, tema_actual='matrices'):
    """Devuelve el id del tema elegido, o None si el jugador pulsó 'Volver'."""
    clock = pygame.time.Clock()
    fondo = get_fondo_menu()

    cols = 3
    card_w, card_h = 320, 214
    gap_x, gap_y = 30, 22
    total_w = cols * card_w + (cols - 1) * gap_x
    x0 = (Config.ANCHO - total_w) // 2
    y0 = 244
    inner_w = card_w - 2 * 18

    rects = {}
    for idx, t in enumerate(TEMAS):
        fila, col = divmod(idx, cols)
        x = x0 + col * (card_w + gap_x)
        y = y0 + fila * (card_h + gap_y)
        rects[t['id']] = pygame.Rect(x, y, card_w, card_h)

    btn_volver = pygame.Rect(40, Config.ALTO - 76, 160, 50)
    aviso = None

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

            ventana.blit(texto(font_small, t['continente'].upper(), (255, 245, 225)), (rect.x + 18, rect.y + 8))
            y = rect.y + 28

            titulo_lineas = _envolver_px(font_large, t['nombre'], inner_w)
            for linea in titulo_lineas:
                ventana.blit(texto(font_large, linea, (255, 255, 255)), (rect.x + 18, y))
                y += 32
            y += 4

            if t['guardian']:
                ventana.blit(texto(font_small, f"Guardián: {t['guardian']}", (255, 236, 200)), (rect.x + 18, y))
                y += 22

            for linea in _envolver_px(font_small, t['resumen'], inner_w)[:2]:
                ventana.blit(texto(font_small, linea, (255, 255, 255)), (rect.x + 18, y))
                y += 19

            if t['disponible']:
                prog = progress.resumen(estudiante, t['id'])
                estado = (f"Mejor: Nivel {prog['mejor_nivel']} · {prog['mejor_puntaje']} pts"
                          if prog['mejor_nivel'] > 0 else "Aún sin jugar")
            else:
                estado = "Próximamente"
            ventana.blit(texto(font_small, estado, (255, 245, 225)), (rect.x + 18, rect.bottom - 28))

        draw_button(ventana, btn_volver, "Volver", mouse_pos, (150, 90, 70), (180, 115, 90), font_obj=font_small)

        if aviso and time.time() - aviso['t0'] < DUR_AVISO:
            contenido = font.render(aviso['texto'], True, (255, 255, 255))
            caja = pygame.Rect(0, 0, contenido.get_width() + 44, 46)
            caja.center = (Config.ANCHO // 2, 198)
            capa = pygame.Surface(caja.size, pygame.SRCALPHA)
            pygame.draw.rect(capa, (*aviso['color'], 235), capa.get_rect(), border_radius=13)
            pygame.draw.rect(capa, (255, 255, 255, 235), capa.get_rect(), 2, border_radius=13)
            capa.blit(contenido, contenido.get_rect(center=(caja.width // 2, caja.height // 2)))
            ventana.blit(capa, caja.topleft)

        pygame.display.flip()
        clock.tick(Config.FPS)
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_volver.collidepoint(event.pos):
                    return None
                for t in TEMAS:
                    if rects[t['id']].collidepoint(event.pos):
                        if t['disponible']:
                            return t['id']
                        aviso = {'texto': f"{t['nombre']} todavía no está listo: ¡vuelve pronto!",
                                'color': (150, 120, 40), 't0': time.time()}
                        break


def _envolver_px(fuente, texto_largo, max_width):
    """Ajuste de texto por ancho real en píxeles (no por conteo de caracteres):
    con fuentes en negrita, una palabra ancha puede desbordar aunque el conteo
    de letras parezca corto, así que medimos con la fuente real."""
    palabras = texto_largo.split()
    if not palabras:
        return []
    lineas, actual = [], palabras[0]
    for palabra in palabras[1:]:
        candidato = actual + ' ' + palabra
        if fuente.size(candidato)[0] <= max_width:
            actual = candidato
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas
