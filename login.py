# login.py
"""Pantalla de inicio de sesión por nombre: varios estudiantes pueden usar el
mismo computador sin mezclar su progreso, porque cada nombre es una llave
distinta dentro de progreso_estudiante.json (ver progress.py). Se muestra una
sola vez al arrancar el juego, justo después del prólogo."""
import json
import os
import sys
import pygame

from config import Config, font, font_large, font_title
from ui import draw_button, get_fondo_menu

_RUTA_ULTIMO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ultimo_estudiante.json')
MAX_LONGITUD = 20


def _cargar_ultimo():
    try:
        with open(_RUTA_ULTIMO, 'r', encoding='utf-8') as f:
            return json.load(f).get('nombre', '')
    except Exception:
        return ''


def _guardar_ultimo(nombre):
    try:
        with open(_RUTA_ULTIMO, 'w', encoding='utf-8') as f:
            json.dump({'nombre': nombre}, f, ensure_ascii=False)
    except Exception:
        pass


def pedir_nombre(ventana):
    """Devuelve el nombre del estudiante (nunca vacío): es el primer paso
    del juego y no se puede saltar, porque de eso depende qué progreso se
    carga después."""
    clock = pygame.time.Clock()
    fondo = get_fondo_menu()
    nombre = _cargar_ultimo()
    activo = True

    caja = pygame.Rect(Config.ANCHO // 2 - 220, 360, 440, 60)
    boton = pygame.Rect(Config.ANCHO // 2 - 110, 444, 220, 56)

    pygame.key.start_text_input()
    try:
        while True:
            ventana.blit(fondo, (0, 0))
            titulo = font_title.render("¿Cómo te llamas?", True, (206, 42, 62))
            ventana.blit(titulo, titulo.get_rect(center=(Config.ANCHO // 2, 220)))
            sub = font.render("Tu nombre guarda tu propio progreso en cada tema.", True, (86, 34, 24))
            ventana.blit(sub, sub.get_rect(center=(Config.ANCHO // 2, 280)))

            mouse_pos = pygame.mouse.get_pos()

            pygame.draw.rect(ventana, (255, 255, 255), caja, border_radius=14)
            pygame.draw.rect(ventana, (206, 42, 62) if activo else (200, 190, 180), caja, 3, border_radius=14)
            contenido = nombre
            if activo and (pygame.time.get_ticks() // 500) % 2 == 0:
                contenido += "|"
            render_txt = font_large.render(contenido or " ", True, (40, 30, 25))
            ventana.blit(render_txt, (caja.x + 16, caja.centery - render_txt.get_height() // 2))

            listo = len(nombre.strip()) > 0
            color_boton = (60, 150, 90) if listo else (190, 185, 180)
            hover_boton = (80, 180, 110) if listo else (190, 185, 180)
            draw_button(ventana, boton, "Comenzar", mouse_pos, color_boton, hover_boton, font_obj=font_large)

            pygame.display.flip()
            clock.tick(Config.FPS)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    activo = caja.collidepoint(ev.pos)
                    if listo and boton.collidepoint(ev.pos):
                        nombre = nombre.strip()
                        _guardar_ultimo(nombre)
                        return nombre
                elif ev.type == pygame.TEXTINPUT and activo:
                    if len(nombre) < MAX_LONGITUD:
                        nombre += ev.text
                elif ev.type == pygame.KEYDOWN and activo:
                    if ev.key == pygame.K_BACKSPACE:
                        nombre = nombre[:-1]
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and listo:
                        nombre = nombre.strip()
                        _guardar_ultimo(nombre)
                        return nombre
    finally:
        pygame.key.stop_text_input()
