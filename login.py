# login.py
"""Pantalla de inicio de sesión por nombre: varios estudiantes pueden usar el
mismo computador sin mezclar su progreso, porque cada nombre es una llave
distinta dentro de progreso_estudiante.json (ver progress.py). Se muestra una
sola vez al arrancar el juego, justo después del prólogo."""
import entrada
import asyncio
import json
import os
import sys
import pygame

from config import Config, font, font_large, font_title
from ui import draw_button, get_fondo_menu

_RUTA_ULTIMO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ultimo_estudiante.json')
MAX_LONGITUD = 20

# -------------------- Teclado en pantalla --------------------
# En el navegador de un celular o tablet el juego vive dentro de un <canvas>, y
# un canvas no abre el teclado del sistema: no hay ningún campo de texto que el
# navegador pueda enfocar, así que `pygame.key.start_text_input()` no muestra
# nada y el estudiante se queda sin poder escribir su nombre. Por eso el juego
# dibuja su propio teclado. Se muestra siempre, también en computadora, para que
# haya un solo camino de código: lo que se prueba en el escritorio es
# exactamente lo que corre en el celular. El teclado físico sigue funcionando.
_FILAS_TECLADO = ("QWERTYUIOP", "ASDFGHJKLÑ", "ZXCVBNM")
_TECLA_ANCHO, _TECLA_ALTO, _SEPARACION = 84, 56, 10
_TECLADO_Y = 525
_COLOR_TECLA = (236, 226, 214)
_COLOR_TECLA_ACTIVA = (255, 206, 150)
_COLOR_TECLA_TEXTO = (70, 45, 35)

_teclado_cache = None


def _construir_teclado():
    """Devuelve la lista de teclas como (rect, etiqueta, (acción, valor))."""
    filas = [[(letra, ('letra', letra), _TECLA_ANCHO) for letra in fila]
             for fila in _FILAS_TECLADO]
    filas[-1].append(("Borrar", ('borrar', None), 150))
    filas.append([("Espacio", ('espacio', None), 420)])

    teclas = []
    for n, fila in enumerate(filas):
        y = _TECLADO_Y + n * (_TECLA_ALTO + _SEPARACION)
        ancho_fila = sum(w for _, _, w in fila) + (len(fila) - 1) * _SEPARACION
        x = (Config.ANCHO - ancho_fila) // 2
        for etiqueta, accion, ancho in fila:
            teclas.append((pygame.Rect(x, y, ancho, _TECLA_ALTO), etiqueta, accion))
            x += ancho + _SEPARACION
    return teclas


def _teclado():
    """Teclas + el teclado ya dibujado en una superficie, construido una sola vez.

    Dibujar las 29 teclas en cada fotograma costaba más de cien operaciones de
    rasterizado por frame, que en WebAssembly se nota. Así solo queda un blit, y
    encima se redibuja únicamente la tecla señalada por el cursor.
    """
    global _teclado_cache
    if _teclado_cache is None:
        teclas = _construir_teclado()
        area = teclas[0][0].unionall([t[0] for t in teclas[1:]]).inflate(16, 16)
        superficie = pygame.Surface(area.size, pygame.SRCALPHA)
        for rect, etiqueta, accion in teclas:
            # mouse_pos imposible: ninguna tecla se dibuja en estado "hover".
            draw_button(superficie, rect.move(-area.x, -area.y), etiqueta, (-1, -1),
                        _COLOR_TECLA, _COLOR_TECLA, text_color=_COLOR_TECLA_TEXTO,
                        font_obj=font_large, radius=10)
        _teclado_cache = (teclas, superficie, area.topleft)
    return _teclado_cache


def _agregar_letra(nombre, letra):
    """Escribe la letra respetando mayúsculas de nombre propio: la inicial de
    cada palabra en mayúscula y el resto en minúscula, para que al tocar el
    teclado salga "Johan Garcia" y no "JOHAN GARCIA"."""
    if not nombre or nombre.endswith(' '):
        return nombre + letra.upper()
    return nombre + letra.lower()


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


async def pedir_nombre(ventana):
    """Devuelve el nombre del estudiante (nunca vacío): es el primer paso
    del juego y no se puede saltar, porque de eso depende qué progreso se
    carga después."""
    clock = pygame.time.Clock()
    fondo = get_fondo_menu()
    nombre = _cargar_ultimo()
    activo = True

    caja = pygame.Rect(Config.ANCHO // 2 - 220, 360, 440, 60)
    boton = pygame.Rect(Config.ANCHO // 2 - 110, 444, 220, 56)
    teclas, superficie_teclado, origen_teclado = _teclado()

    # Al venir de la cinemática puede quedar un toque sin procesar en la cola;
    # sin descartarlo bastaría para pulsar "Comenzar" y saltarse esta pantalla
    # cuando ya hay un nombre guardado de la sesión anterior.
    pygame.event.clear()

    # La cinemática termina en negro; esta pantalla aparece desde negro en vez
    # de saltar de golpe a su fondo crema, que se veía como un fogonazo.
    velo_negro = pygame.Surface((Config.ANCHO, Config.ALTO)).convert()
    velo_negro.fill((0, 0, 0))
    t_entrada = pygame.time.get_ticks()

    pygame.key.start_text_input()
    try:
        while True:
            ventana.blit(fondo, (0, 0))
            titulo = font_title.render("¿Cómo te llamas?", True, (206, 42, 62))
            ventana.blit(titulo, titulo.get_rect(center=(Config.ANCHO // 2, 220)))
            sub = font.render("Tu nombre guarda tu propio progreso en cada tema.", True, (86, 34, 24))
            ventana.blit(sub, sub.get_rect(center=(Config.ANCHO // 2, 280)))

            mouse_pos = entrada.posicion_puntero()

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

            ventana.blit(superficie_teclado, origen_teclado)
            for rect, etiqueta, accion in teclas:
                if rect.collidepoint(mouse_pos):
                    draw_button(ventana, rect, etiqueta, mouse_pos, _COLOR_TECLA,
                                _COLOR_TECLA_ACTIVA, text_color=_COLOR_TECLA_TEXTO,
                                font_obj=font_large, radius=10)
                    break

            aparicion = min(1.0, (pygame.time.get_ticks() - t_entrada) / 600.0)
            if aparicion < 1.0:
                velo_negro.set_alpha(int(255 * (1 - aparicion) ** 2))
                ventana.blit(velo_negro, (0, 0))

            pygame.display.flip()
            clock.tick(Config.FPS)
            await asyncio.sleep(0)

            for ev in entrada.obtener_eventos():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    activo = caja.collidepoint(ev.pos)
                    if listo and boton.collidepoint(ev.pos):
                        nombre = nombre.strip()
                        _guardar_ultimo(nombre)
                        return nombre
                    for rect, _etiqueta, (accion, valor) in teclas:
                        if not rect.collidepoint(ev.pos):
                            continue
                        # Tocar el teclado da el foco a la caja: en una pantalla
                        # táctil nadie va a tocar primero la caja y luego la tecla.
                        activo = True
                        if accion == 'letra' and len(nombre) < MAX_LONGITUD:
                            nombre = _agregar_letra(nombre, valor)
                        elif accion == 'borrar':
                            nombre = nombre[:-1]
                        elif (accion == 'espacio' and nombre.strip()
                                and not nombre.endswith(' ') and len(nombre) < MAX_LONGITUD):
                            nombre += ' '
                        break
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
