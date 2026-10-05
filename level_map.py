# level_map.py
"""Camino de niveles: se muestra al elegir un tema, antes de jugar.

Es un mapa de aventura: un sendero punteado que serpentea por el continente,
con un nodo por nivel (1..Config.MAX_LEVEL). Los niveles bloqueados llevan un
candado y no se pueden pulsar; el nivel que toca jugar late. Al final del
camino espera El Vacío, el jefe que aparece en cada subida de nivel (boss.py),
y abajo la guardiana o guardián del continente dice una de sus frases del lore.

Antes era una línea recta de cinco círculos en medio de una pantalla vacía.
Superar un nivel desbloquea el siguiente (progress.desbloquear_nivel, llamado
desde cada minijuego).
"""
import asyncio
import math
import sys

import pygame
import pygame.gfxdraw

import entrada
import progress
from config import Config, font, font_small, font_large, font_title
from fuentes import fuente, TITULO, TITULO_SUAVE, TEXTO_FUERTE
from lore import CONTINENTES
from topics import tema as info_tema
from ui import draw_button, texto, get_fondo_menu, draw_circle_aa, draw_ring_aa

NODO_RADIO = 44


def _estrella(surface, center, radio, color):
    cx, cy = center
    pts = []
    for k in range(10):
        r = radio if k % 2 == 0 else radio * 0.45
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pygame.gfxdraw.filled_polygon(surface, pts, color)
    pygame.gfxdraw.aapolygon(surface, pts, color)


def _candado(surface, center, color):
    """Candado pequeño dibujado con primitivas, para los niveles bloqueados."""
    cx, cy = center
    cuerpo = pygame.Rect(0, 0, 22, 17)
    cuerpo.midtop = (cx, cy - 1)
    pygame.draw.arc(surface, color, (cx - 8, cy - 15, 16, 22), 0, math.pi, 3)
    pygame.draw.rect(surface, color, cuerpo, border_radius=4)
    pygame.draw.circle(surface, (235, 230, 224), (cx, cuerpo.y + 7), 3)


def _oscurecer(color, k):
    return tuple(int(c * k) for c in color)


def _catmull_rom(puntos, pasos=24):
    """Curva suave que pasa por todos los puntos (el sendero)."""
    if len(puntos) < 2:
        return list(puntos)
    ext = [puntos[0]] + list(puntos) + [puntos[-1]]
    curva = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(pasos):
            t = s / pasos
            t2, t3 = t * t, t * t * t
            curva.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t
                                      + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                      + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in range(2)))
    curva.append(puntos[-1])
    return curva


def _puntos_a_distancia(curva, separacion):
    """Puntos equiespaciados sobre la curva, para dibujarla punteada."""
    salida = [curva[0]]
    resto = 0.0
    for a, b in zip(curva, curva[1:]):
        largo = math.dist(a, b)
        d = separacion - resto
        while d <= largo:
            k = d / largo
            salida.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
            d += separacion
        resto = largo - (d - separacion)
    return salida


def _vacio_en_miniatura(surface, center, t):
    """El Vacío esperando al final del sendero: el mismo orbe del jefe."""
    cx, cy = center
    r = int(30 + 2 * math.sin(t * 2.6))
    for g, col in ((8, (236, 196, 206)), (4, (226, 150, 170))):
        pygame.gfxdraw.filled_circle(surface, cx, cy, r + g, col)
    pygame.gfxdraw.filled_circle(surface, cx, cy, r, (14, 6, 18))
    pygame.gfxdraw.aacircle(surface, cx, cy, r, (232, 58, 108))
    cero = texto(fuente(TITULO, 34), "0", (255, 96, 128))
    surface.blit(cero, cero.get_rect(center=(cx, cy + 1)))


async def mostrar_mapa_niveles(ventana, tema_id, estudiante):
    """Devuelve el nivel elegido (int) para empezar a jugar, o None si el
    jugador pulsó 'Volver'."""
    clock = pygame.time.Clock()
    fondo = get_fondo_menu()
    info = info_tema(tema_id)
    color = info['color']
    lore = CONTINENTES.get(tema_id, {})

    f_nivel = fuente(TITULO_SUAVE, 21)
    f_guardian = fuente(TITULO_SUAVE, 23)
    f_cita = fuente(TEXTO_FUERTE, 18)
    f_badge = fuente(TEXTO_FUERTE, 14)

    n = Config.MAX_LEVEL
    x_ini, x_fin = 160, 965
    espacio = (x_fin - x_ini) / max(1, n - 1)
    centros = [(int(x_ini + i * espacio), 318 if i % 2 == 0 else 418) for i in range(n)]
    nodos = []
    for c in centros:
        r = pygame.Rect(0, 0, NODO_RADIO * 2, NODO_RADIO * 2)
        r.center = c
        nodos.append(r)
    pos_vacio = (1110, 352)

    # El sendero empieza fuera de la pantalla por la izquierda y termina en El Vacío
    curva = _catmull_rom([(30, 380)] + centros + [pos_vacio])
    puntos_sendero = _puntos_a_distancia(curva, 17)
    # índice del punto del sendero más cercano a cada nodo (para pintar el avance)
    idx_nodo = [min(range(len(puntos_sendero)), key=lambda k: math.dist(puntos_sendero[k], c))
                for c in centros]

    tarjeta = pygame.Rect(Config.ANCHO // 2 - 420, 566, 840, 112)
    btn_volver = pygame.Rect(40, Config.ALTO - 84, 190, 56)

    while True:
        t = pygame.time.get_ticks() / 1000.0
        desbloqueado = progress.nivel_desbloqueado(estudiante, tema_id)
        completados = min(n, max(0, desbloqueado - 1))

        ventana.blit(fondo, (0, 0))
        titulo = texto(font_title, info['continente'], _oscurecer(color, 0.82))
        ventana.blit(titulo, titulo.get_rect(center=(Config.ANCHO // 2, 84)))
        sub = texto(font, f"{info['nombre']}  ·  elige un nivel, {estudiante}", (110, 60, 44))
        ventana.blit(sub, sub.get_rect(center=(Config.ANCHO // 2, 132)))

        mouse_pos = entrada.posicion_puntero()

        # Sendero: recorrido en el color del tema, lo que falta en tono arena
        limite = idx_nodo[min(n - 1, max(0, desbloqueado - 1))]
        for k, p in enumerate(puntos_sendero):
            recorrido = k <= limite
            draw_circle_aa(ventana, p, 5 if recorrido else 4,
                           color if recorrido else (214, 188, 166))

        _vacio_en_miniatura(ventana, pos_vacio, t)
        etq_vacio = texto(f_badge, "El Vacío espera", (150, 60, 86))
        ventana.blit(etq_vacio, etq_vacio.get_rect(midtop=(pos_vacio[0], pos_vacio[1] + 44)))

        for i, rect in enumerate(nodos):
            nivel = i + 1
            bloqueado = nivel > desbloqueado
            completado = nivel < desbloqueado
            actual = not bloqueado and not completado
            hover = rect.collidepoint(mouse_pos) and not bloqueado

            if bloqueado:
                base = (204, 196, 188)
            elif completado:
                base = color
            else:
                base = color
            if hover:
                base = tuple(min(255, int(c * 1.12)) for c in base)

            radio = NODO_RADIO
            if actual:
                # El nivel que toca jugar late y tiene un halo
                radio = int(NODO_RADIO * (1 + 0.05 * math.sin(t * 4)))
                draw_ring_aa(ventana, rect.center, radio + 12, 4,
                             tuple(min(255, int(c * 0.5 + 128)) for c in color))
            draw_circle_aa(ventana, (rect.centerx, rect.centery + 5), radio, _oscurecer(base, 0.55))
            draw_circle_aa(ventana, rect.center, radio, base)
            draw_ring_aa(ventana, rect.center, radio, 4,
                         (255, 255, 255) if not bloqueado else (176, 168, 160))

            if completado:
                _estrella(ventana, (rect.centerx, rect.centery - 1), 18, (255, 255, 255))
            elif bloqueado:
                _candado(ventana, (rect.centerx, rect.centery - 2), (150, 142, 134))
            else:
                num = texto(font_large, str(nivel), (255, 255, 255))
                ventana.blit(num, num.get_rect(center=rect.center))

            if actual:
                badge = texto(f_badge, "¡Juega!", (255, 255, 255))
                caja = badge.get_rect(midbottom=(rect.centerx, rect.top - 20)).inflate(18, 8)
                pygame.draw.rect(ventana, _oscurecer(color, 0.8), caja, border_radius=10)
                ventana.blit(badge, badge.get_rect(center=caja.center))

            nombre_nivel = texto(f_nivel, f"Nivel {nivel}",
                                 (96, 70, 58) if not bloqueado else (160, 146, 136))
            ventana.blit(nombre_nivel, nombre_nivel.get_rect(midtop=(rect.centerx, rect.bottom + 12)))
            detalle = "Bloqueado" if bloqueado else f"Meta: {Config.GOAL_BASE * nivel} pts"
            det = texto(font_small, detalle, (130, 100, 84) if not bloqueado else (168, 154, 144))
            ventana.blit(det, det.get_rect(midtop=(rect.centerx, rect.bottom + 38)))

        # Tarjeta del guardián del continente, con una frase suya del lore
        pygame.draw.rect(ventana, (150, 110, 90), tarjeta.move(0, 5), border_radius=18)
        pygame.draw.rect(ventana, (255, 250, 244), tarjeta, border_radius=18)
        pygame.draw.rect(ventana, color, (tarjeta.x, tarjeta.y, 12, tarjeta.height),
                         border_top_left_radius=18, border_bottom_left_radius=18)
        if lore:
            # Redacción neutra: el lore no fija el género de quien custodia cada continente
            guardian = texto(f_guardian, f"{lore['guardian']}, desde {lore['continente']}:",
                             _oscurecer(color, 0.75))
            ventana.blit(guardian, (tarjeta.x + 36, tarjeta.y + 18))
            frase = lore['entrada'][-1]
            cita = texto(f_cita, f"«{frase}»", (88, 64, 56))
            ventana.blit(cita, (tarjeta.x + 36, tarjeta.y + 60))

        if completados >= n:
            logro = texto(font, "¡Completaste todos los niveles de este tema!", (56, 132, 86))
        else:
            logro = texto(font, f"Niveles superados: {completados} de {n}", (110, 72, 58))
        ventana.blit(logro, logro.get_rect(midright=(Config.ANCHO - 44, btn_volver.centery)))

        draw_button(ventana, btn_volver, "Volver", mouse_pos, (160, 98, 76), (188, 124, 98),
                    font_obj=fuente(TITULO_SUAVE, 24))

        pygame.display.flip()
        clock.tick(Config.FPS)
        await asyncio.sleep(0)

        for event in entrada.obtener_eventos():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_volver.collidepoint(event.pos):
                    return None
                for i, rect in enumerate(nodos):
                    nivel = i + 1
                    if nivel <= desbloqueado and rect.collidepoint(event.pos):
                        return nivel
