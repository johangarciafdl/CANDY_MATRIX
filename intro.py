# intro.py
"""Prólogo cinemático de apertura (GDD sección 5.1: "Prólogo cinematográfico"),
adaptado a texto en pantalla porque este proyecto no tiene actores de voz.
Es 100% procedural (sin imágenes ni video): números que forman una matriz,
la matriz se rompe en fragmentos hacia Matrixia, y el título aparece. Se
puede saltar en cualquier momento con un clic, una tecla o ESC."""
import entrada
import asyncio
import math
import random
import time
import pygame

from config import Config, COLOR_MAP, font, font_small, font_large, font_title
from ui import draw_circle_aa
import effects

GRID = 6
CELDA = 48

DUR_FRAGMENTOS = 2.0
DUR_FORMACION = 2.0
DUR_COMPLETA = 2.4
DUR_RUPTURA = 2.2
DUR_SOMBRA = 2.0
DUR_TITULO = 3.4
TOTAL = DUR_FRAGMENTOS + DUR_FORMACION + DUR_COMPLETA + DUR_RUPTURA + DUR_SOMBRA + DUR_TITULO

TITULO_STR = "CANDY MATRIX"
LETRAS_POR_SEGUNDO = 14

# Margen antes de permitir que un clic salte la cinemática. En el navegador el
# juego no arranca hasta que el usuario toca la pantalla (lo exige el navegador
# para poder reproducir audio), y ese mismo toque llega al canvas como un clic:
# sin este margen la cinemática se saltaba sola en el celular.
ESPERA_ANTES_DE_SALTAR = 0.8

_CACHE_GLIFO = {}


def _ease(t):
    """Arranca y termina suave, igual que el resto de las animaciones del juego."""
    return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2


def _glifo_base(valor):
    if valor not in _CACHE_GLIFO:
        s = pygame.Surface((CELDA - 6, CELDA - 6), pygame.SRCALPHA)
        color = COLOR_MAP[valor]
        pygame.draw.rect(s, color, s.get_rect(), border_radius=10)
        pygame.draw.rect(s, tuple(int(c * 0.65) for c in color), s.get_rect(), 2, border_radius=10)
        num = font_large.render(str(valor), True, (255, 255, 255))
        s.blit(num, num.get_rect(center=(s.get_width() // 2, s.get_height() // 2)))
        _CACHE_GLIFO[valor] = s
    return _CACHE_GLIFO[valor]


def _dibujar_glifo(surface, x, y, valor, alpha):
    if alpha <= 0:
        return
    base = _glifo_base(valor).copy()
    base.set_alpha(max(0, min(255, int(alpha))))
    surface.blit(base, base.get_rect(center=(int(x), int(y))))


def _texto_narrativo(surface, texto_str, t_fase, duracion_fase, y=None):
    """Aparece y se desvanece dentro de su fase, para que el corte a la
    siguiente escena nunca se sienta abrupto."""
    fade_in = min(1.0, t_fase / 0.5)
    fade_out = min(1.0, max(0.0, (duracion_fase - t_fase) / 0.5))
    alpha = int(255 * min(fade_in, fade_out))
    if alpha <= 0:
        return
    render = font.render(texto_str, True, (235, 225, 215))
    render.set_alpha(alpha)
    surface.blit(render, render.get_rect(center=(Config.ANCHO // 2, y or Config.ALTO - 90)))


def _dibujar_chispa(surface, cx, cy, t):
    """El 'Aprendiz de Matriz': un resplandor pulsante, ya que no hay arte de
    personaje en un juego dibujado con primitivas de pygame."""
    pulso = 1.0 + 0.18 * math.sin(t * 4)
    for radio, alpha in ((46, 35), (30, 70), (16, 140), (7, 255)):
        r = radio * pulso
        capa = pygame.Surface((int(r * 2) + 4, int(r * 2) + 4), pygame.SRCALPHA)
        draw_circle_aa(capa, (capa.get_width() // 2, capa.get_height() // 2), r, (255, 222, 150, alpha))
        surface.blit(capa, capa.get_rect(center=(cx, cy)))


async def mostrar_intro(ventana, sound=None):
    """Corre la cinemática una sola vez, al arrancar el juego. Se puede saltar
    con clic, tecla o ESC en cualquier momento. `sound` es el SoundManager ya
    creado (sin música de fondo todavía): cada beat de la historia dispara su
    propio efecto, y el título suena letra por letra al aparecer."""
    clock = pygame.time.Clock()
    effects.limpiar()

    def _play(nombre):
        if sound:
            sound.play(nombre)

    sonido_matriz_hecho = False
    sonido_ruptura_hecho = False
    sonido_chispa_hecho = False
    letras_reveladas = 0
    sonido_final_hecho = False

    cx, cy = Config.ANCHO // 2, Config.ALTO // 2 - 20
    grid_w = GRID * CELDA
    origen_x = cx - grid_w // 2
    origen_y = cy - grid_w // 2

    fragmentos = []
    for i in range(GRID):
        for j in range(GRID):
            fragmentos.append({
                'valor': random.randrange(len(COLOR_MAP)),
                'inicio': (random.uniform(40, Config.ANCHO - 40), random.uniform(40, Config.ALTO - 40)),
                'destino': (origen_x + j * CELDA + CELDA // 2, origen_y + i * CELDA + CELDA // 2),
                'fase_offset': random.uniform(0, 0.5),
                'angulo': random.uniform(0, 2 * math.pi),
                'bob_fase': random.uniform(0, math.tau),
                'estallo_hecho': False,
            })

    # Descarta el toque/clic con el que el navegador arrancó el juego, que de
    # otro modo quedaría en la cola y saltaría la cinemática en el primer frame.
    pygame.event.clear()
    t0 = time.time()

    while True:
        t = time.time() - t0
        if t >= TOTAL:
            return

        for ev in entrada.obtener_eventos():
            if ev.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if (t >= ESPERA_ANTES_DE_SALTAR
                    and ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN)):
                return

        ventana.fill((8, 8, 14))
        ahora = time.time()

        if t < DUR_FRAGMENTOS + DUR_FORMACION:
            # ---------- Fase 1+2: fragmentos numéricos que forman la matriz ----------
            for f in fragmentos:
                t_local = max(0.0, t - f['fase_offset'])
                if t < DUR_FRAGMENTOS:
                    duracion_local = max(0.3, DUR_FRAGMENTOS - f['fase_offset'])
                    alpha = min(255, int(255 * (t_local / duracion_local)))
                    bob = 6 * math.sin(ahora * 3 + f['bob_fase'])
                    x, y = f['inicio'][0], f['inicio'][1] + bob
                else:
                    p = _ease(min(1.0, (t - DUR_FRAGMENTOS) / DUR_FORMACION))
                    x = f['inicio'][0] + (f['destino'][0] - f['inicio'][0]) * p
                    y = f['inicio'][1] + (f['destino'][1] - f['inicio'][1]) * p
                    alpha = 255
                _dibujar_glifo(ventana, x, y, f['valor'], alpha)

        elif t < DUR_FRAGMENTOS + DUR_FORMACION + DUR_COMPLETA:
            # ---------- Fase 3: la matriz central, completa ----------
            if not sonido_matriz_hecho:
                _play('chime')
                sonido_matriz_hecho = True
            for f in fragmentos:
                _dibujar_glifo(ventana, *f['destino'], f['valor'], 255)
            t_fase = t - (DUR_FRAGMENTOS + DUR_FORMACION)
            _texto_narrativo(ventana, "Antes de que existieran los mundos, existía una sola matriz.",
                             t_fase, DUR_COMPLETA)

        elif t < DUR_FRAGMENTOS + DUR_FORMACION + DUR_COMPLETA + DUR_RUPTURA:
            # ---------- Fase 4: la matriz se rompe hacia Matrixia ----------
            if not sonido_ruptura_hecho:
                _play('shatter')
                sonido_ruptura_hecho = True
            t_fase = t - (DUR_FRAGMENTOS + DUR_FORMACION + DUR_COMPLETA)
            p = min(1.0, t_fase / DUR_RUPTURA)
            pe = _ease(p)
            for f in fragmentos:
                if not f['estallo_hecho'] and p > 0.02:
                    effects.spawn_burst(*f['destino'], COLOR_MAP[f['valor']], cantidad=4, velocidad=90)
                    f['estallo_hecho'] = True
                dist = 560 * pe
                x = f['destino'][0] + math.cos(f['angulo']) * dist
                y = f['destino'][1] + math.sin(f['angulo']) * dist
                _dibujar_glifo(ventana, x, y, f['valor'], max(0, int(255 * (1 - p))))
            sombra = pygame.Surface((Config.ANCHO, Config.ALTO), pygame.SRCALPHA)
            sombra.fill((0, 0, 0, int(190 * p)))
            ventana.blit(sombra, (0, 0))
            _texto_narrativo(ventana, "El conocimiento no desapareció. Se fragmentó.", t_fase, DUR_RUPTURA)

        elif t < DUR_FRAGMENTOS + DUR_FORMACION + DUR_COMPLETA + DUR_RUPTURA + DUR_SOMBRA:
            # ---------- Fase 5: la sombra y el Aprendiz de Matriz ----------
            if not sonido_chispa_hecho:
                _play('chime')
                sonido_chispa_hecho = True
            t_fase = t - (DUR_FRAGMENTOS + DUR_FORMACION + DUR_COMPLETA + DUR_RUPTURA)
            _dibujar_chispa(ventana, cx, cy - 20, ahora)
            _texto_narrativo(ventana, "Ahora alguien tendrá que reconstruirla.", t_fase, DUR_SOMBRA)

        else:
            # ---------- Fase 6: título, letra por letra y sincronizado con sonido ----------
            t_fase = t - (TOTAL - DUR_TITULO)
            n_visibles = min(len(TITULO_STR), int(t_fase * LETRAS_POR_SEGUNDO))
            if n_visibles > letras_reveladas:
                for idx in range(letras_reveladas, n_visibles):
                    if TITULO_STR[idx] != ' ':
                        _play('explosion')  # "pop" suave, una por letra
                letras_reveladas = n_visibles

            titulo = font_title.render(TITULO_STR[:n_visibles], True, (216, 52, 72))
            ventana.blit(titulo, titulo.get_rect(center=(cx, cy - 10)))

            t_titulo_completo = len(TITULO_STR) / LETRAS_POR_SEGUNDO
            if n_visibles >= len(TITULO_STR):
                if not sonido_final_hecho:
                    _play('levelup')
                    sonido_final_hecho = True
                t_desde_completo = t_fase - t_titulo_completo
                sub = font.render("El conocimiento está en tus manos.", True, (230, 215, 205))
                sub.set_alpha(int(255 * min(1.0, max(0.0, t_desde_completo) / 0.7)))
                ventana.blit(sub, sub.get_rect(center=(cx, cy + 44)))
                if t_fase > 2.4:
                    aviso = font_small.render("Toca cualquier tecla para continuar", True, (150, 145, 150))
                    ventana.blit(aviso, aviso.get_rect(center=(cx, cy + 96)))

        effects.update_and_draw(ventana, 1.0 / Config.FPS)
        pygame.display.flip()
        clock.tick(Config.FPS)
        await asyncio.sleep(0)
