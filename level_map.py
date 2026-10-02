# level_map.py
"""Camino de niveles: se muestra al elegir un tema, antes de jugar. Cada nodo
es un nivel (1..Config.MAX_LEVEL); los que todavía no se desbloquean se ven
apagados y no se pueden pulsar. Superar un nivel desbloquea el siguiente
(progress.desbloquear_nivel, llamado desde cada minijuego)."""
import asyncio
import math
import sys
import pygame

from config import Config, font, font_small, font_large, font_title
from ui import draw_button, texto, get_fondo_menu, draw_circle_aa, draw_ring_aa
from topics import tema as info_tema
import progress

NODO_RADIO = 40


def _estrella(surface, center, radio, color):
    cx, cy = center
    pts = []
    for k in range(10):
        r = radio if k % 2 == 0 else radio * 0.45
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pygame.draw.polygon(surface, color, pts)


async def mostrar_mapa_niveles(ventana, tema_id, estudiante):
    """Devuelve el nivel elegido (int) para empezar a jugar, o None si el
    jugador pulsó 'Volver'."""
    clock = pygame.time.Clock()
    fondo = get_fondo_menu()
    info = info_tema(tema_id)

    n = Config.MAX_LEVEL
    espacio = min(170, (Config.ANCHO - 240) // max(1, n - 1))
    total_w = espacio * (n - 1)
    x0 = (Config.ANCHO - total_w) // 2
    y_nodos = 420
    nodos = [pygame.Rect(0, 0, NODO_RADIO * 2, NODO_RADIO * 2) for _ in range(n)]
    for i, r in enumerate(nodos):
        r.center = (x0 + i * espacio, y_nodos)

    btn_volver = pygame.Rect(40, Config.ALTO - 76, 160, 50)

    while True:
        desbloqueado = progress.nivel_desbloqueado(estudiante, tema_id)

        ventana.blit(fondo, (0, 0))
        titulo = font_title.render(info['continente'], True, info['color'])
        ventana.blit(titulo, titulo.get_rect(center=(Config.ANCHO // 2, 120)))
        sub = font.render(f"{info['nombre']} · elige un nivel, {estudiante}", True, (86, 34, 24))
        ventana.blit(sub, sub.get_rect(center=(Config.ANCHO // 2, 168)))

        mouse_pos = pygame.mouse.get_pos()

        if len(nodos) > 1:
            pygame.draw.line(ventana, (210, 190, 175), nodos[0].center, nodos[-1].center, 8)
            avance = nodos[min(len(nodos) - 1, max(0, desbloqueado - 1))].center
            pygame.draw.line(ventana, info['color'], nodos[0].center, avance, 8)

        for i, rect in enumerate(nodos):
            nivel = i + 1
            bloqueado = nivel > desbloqueado
            completado = nivel < desbloqueado

            if bloqueado:
                base = (190, 185, 178)
            elif completado:
                base = tuple(min(255, int(c * 1.05)) for c in info['color'])
            else:
                base = info['color']
            hover = rect.collidepoint(mouse_pos) and not bloqueado
            color_fondo = tuple(min(255, int(c * 1.15)) for c in base) if hover else base

            draw_circle_aa(ventana, rect.center, NODO_RADIO + 3, tuple(int(c * 0.55) for c in color_fondo))
            draw_circle_aa(ventana, rect.center, NODO_RADIO, color_fondo)
            draw_ring_aa(ventana, rect.center, NODO_RADIO, 3,
                        (255, 255, 255) if not bloqueado else (150, 145, 140))

            if completado:
                _estrella(ventana, (rect.centerx, rect.centery - 1), 13, (255, 255, 255))
            else:
                color_num = (255, 255, 255) if not bloqueado else (140, 135, 130)
                num = texto(font_large, str(nivel), color_num)
                ventana.blit(num, num.get_rect(center=rect.center))

            etiqueta = "Bloqueado" if bloqueado else f"Meta: {Config.GOAL_BASE * nivel} pts"
            et = texto(font_small, etiqueta, (120, 90, 70))
            ventana.blit(et, et.get_rect(midtop=(rect.centerx, rect.bottom + 8)))

        if desbloqueado > Config.MAX_LEVEL - 1:
            logro = texto(font, "¡Completaste todos los niveles de este tema!", (56, 132, 86))
            ventana.blit(logro, logro.get_rect(center=(Config.ANCHO // 2, y_nodos + 90)))

        draw_button(ventana, btn_volver, "Volver", mouse_pos, (150, 90, 70), (180, 115, 90), font_obj=font_small)

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
                for i, rect in enumerate(nodos):
                    nivel = i + 1
                    if nivel <= desbloqueado and rect.collidepoint(event.pos):
                        return nivel
