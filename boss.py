# boss.py
"""El Vacío: el antagonista de Matrixia (GDD sección 11 — "entidad negra de
matrices fracturadas con símbolo 0", personalidad intimidante). En vez de
esperar al capítulo final, aquí aparece cada vez que el jugador sube de
nivel en cualquier tema: el juego se pausa y El Vacío se burla del progreso
con una frase al azar, antes de dejar seguir. Más de 50 frases para que no
se repita seguido en una sesión larga."""
import math
import random
import sys
import pygame

from config import Config, font, font_large, font_title
from ui import draw_button, texto, draw_circle_aa
import effects

FRASES = [
    "Muy rápido... pero no tanto para detenerme.",
    "Avanzas rápido. Yo tengo toda la eternidad.",
    "Un nivel más. Como si eso cambiara algo.",
    "¿Cuántas veces necesitas equivocarte antes de aceptar que no puedes?",
    "El conocimiento no se acumula. Se fragmenta. Como tú lo harás.",
    "Sigue sumando puntos. Yo sigo restando tu tiempo.",
    "Cada matriz que resuelves es una grieta más en mi paciencia. Casi.",
    "No te felicito. Todavía.",
    "¿Crees que esto es progreso? Es solo ruido antes del silencio.",
    "El Núcleo sigue roto. Un nivel no lo arregla.",
    "Interesante. Nadie llega tan lejos... dos veces.",
    "Sigues aquí. Curioso.",
    "Cada acierto tuyo es un paso más cerca del error que te detendrá.",
    "No hay prisa. El vacío siempre espera al final.",
    "Tu velocidad me divierte. Tu resistencia, no tanto.",
    "Un nivel superado no es una victoria. Es una invitación.",
    "Sigue jugando. Quiero ver cuándo te detienes.",
    "¿Determinante distinto de cero? Qué optimista.",
    "Las matrices se rompen. Los estudiantes también.",
    "No confundas velocidad con comprensión.",
    "Sigue sumando filas. Yo sigo contando tus errores futuros.",
    "Cada vez que avanzas, yo aprendo cómo detenerte.",
    "El siguiente nivel no te espera con más gentileza que este.",
    "Tu progreso es temporal. Mi paciencia, infinita.",
    "¿Otro nivel? Qué persistente. Qué inútil.",
    "No es el tablero lo que debes temer. Soy yo.",
    "Sigue resolviendo. Yo sigo observando.",
    "Una matriz invertible no significa un jugador invencible.",
    "El siguiente desafío ya sabe tu nombre.",
    "Cuanto más aprendes, más tengo que fragmentar.",
    "No hay determinante que calcule cuánto durarás.",
    "Sigue así. Me gusta ver cómo se agota la esperanza, nivel por nivel.",
    "¿Sientes el progreso? Yo solo siento el tiempo pasar.",
    "Una victoria pequeña no reconstruye un núcleo roto.",
    "Vas bien. Para lo que dura.",
    "El siguiente guardián no podrá protegerte de mí.",
    "Sigue subiendo de nivel. Yo sigo bajando tu confianza.",
    "No temas equivocarte. Teme seguir intentándolo sin comprender.",
    "Cada fragmento que reconstruyes, yo lo vuelvo a romper en otro lugar.",
    "¿Superaste el nivel? Yo superé tu expectativa de que me detendría.",
    "Tu progreso me resulta... familiar. Todos empiezan así.",
    "No busques el final. El final te está buscando a ti.",
    "Un paso más cerca de mí no es un paso más cerca de ganar.",
    "Sigue jugando. Cuanto más aprendas, más interesante será tu caída.",
    "El vacío no se llena con niveles superados.",
    "Bien hecho. Ahora hazlo mil veces más y hablamos.",
    "No soy tu enemigo. Soy tu límite.",
    "Cada vez que aciertas, en algún lugar, una matriz se fragmenta más.",
    "Sigue corriendo. Yo ya estoy en el siguiente nivel, esperándote.",
    "El tiempo que ganas aquí, yo lo cobro después.",
    "Interesante estrategia. Sigue sin comprenderme.",
    "No hay algoritmo que me resuelva.",
    "Un nivel superado es solo un error que decidiste no cometer. Todavía.",
    "Sigue. Quiero ver hasta dónde llega tu paciencia antes que la mía.",
    "El conocimiento que buscas ya sabe que no lo alcanzarás a tiempo.",
    "Cuánta prisa. Como si el tiempo fuera tuyo.",
    "No hay puntuación que mida lo que realmente estás perdiendo.",
    "Sigue jugando. Es lo único que puedes hacer.",
    "Cada nivel es un peldaño. Hacia mí.",
    "Cuando termines, entenderás que apenas empezabas.",
    "Rápido, sí. Pero la velocidad no rompe el silencio que dejo atrás.",
]

_ANGULOS_PICOS = [random.uniform(-0.18, 0.18) for _ in range(14)]


def _envolver_px(fuente, texto_largo, max_width):
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


def _dibujar_boss(surface, cx, cy, t, escala):
    """Silueta oscura y espinosa con un '0' fracturado brillando en el centro:
    'El Vacío' del GDD, dibujado con primitivas (sin arte externo)."""
    radio_base = 130 * escala
    puntas = len(_ANGULOS_PICOS)
    puntos = []
    for k in range(puntas):
        a = (2 * math.pi * k / puntas) + _ANGULOS_PICOS[k]
        pulso = 1.0 + 0.06 * math.sin(t * 2.3 + k)
        r = radio_base * (1.0 if k % 2 == 0 else 0.68) * pulso
        puntos.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    if len(puntos) >= 3:
        pygame.draw.polygon(surface, (18, 12, 20), puntos)
        pygame.draw.polygon(surface, (70, 22, 30), puntos, 3)

    pulso_nucleo = 1.0 + 0.12 * math.sin(t * 4)
    for radio, alpha in ((70, 30), (46, 60), (26, 130), (12, 230)):
        r = radio * pulso_nucleo * escala
        capa = pygame.Surface((int(r * 2) + 4, int(r * 2) + 4), pygame.SRCALPHA)
        draw_circle_aa(capa, (capa.get_width() // 2, capa.get_height() // 2), r, (200, 40, 55, alpha))
        surface.blit(capa, capa.get_rect(center=(cx, cy)))

    cero = font_title.render("0", True, (250, 235, 235))
    cero.set_alpha(int(255 * escala))
    surface.blit(cero, cero.get_rect(center=(cx, cy)))


def mostrar_boss(ventana, sound, nivel_completado, tema_nombre):
    """Modal bloqueante: pausa el juego y muestra a El Vacío burlándose del
    nivel recién superado. Vuelve cuando el jugador pulsa 'Continuar'."""
    clock = pygame.time.Clock()
    frase = random.choice(FRASES)
    t0 = pygame.time.get_ticks() / 1000.0
    if sound:
        sound.play('shatter')

    cx, cy = Config.ANCHO // 2, Config.ALTO // 2 - 90
    caja = pygame.Rect(Config.ANCHO // 2 - 460, Config.ALTO - 230, 920, 130)
    boton = pygame.Rect(Config.ANCHO // 2 - 130, Config.ALTO - 78, 260, 54)
    lineas = _envolver_px(font_large, frase, caja.width - 60)

    while True:
        t = pygame.time.get_ticks() / 1000.0 - t0
        entrada = min(1.0, t / 0.6)
        escala = entrada * entrada * (3 - 2 * entrada)  # smoothstep

        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif entrada >= 1.0 and ev.type == pygame.MOUSEBUTTONDOWN and boton.collidepoint(ev.pos):
                return
            elif entrada >= 1.0 and ev.type == pygame.KEYDOWN and ev.key in (
                    pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE):
                return

        ventana.fill((6, 4, 10))
        _dibujar_boss(ventana, cx, cy, t, max(0.05, escala))

        etiqueta = texto(font, f"El Vacío — Nivel {nivel_completado} de {tema_nombre} superado",
                         (150, 120, 125))
        etiqueta.set_alpha(int(255 * entrada))
        ventana.blit(etiqueta, etiqueta.get_rect(center=(Config.ANCHO // 2, caja.y - 22)))

        if entrada >= 1.0:
            pygame.draw.rect(ventana, (24, 18, 26), caja, border_radius=16)
            pygame.draw.rect(ventana, (90, 30, 40), caja, 2, border_radius=16)
            y = caja.centery - (len(lineas) * 17)
            for linea in lineas:
                render = font_large.render(linea, True, (240, 225, 225))
                ventana.blit(render, render.get_rect(center=(caja.centerx, y)))
                y += 34
            draw_button(ventana, boton, "Continuar", mouse_pos, (110, 40, 50), (140, 60, 70))

        effects.update_and_draw(ventana, 1.0 / Config.FPS)
        pygame.display.flip()
        clock.tick(Config.FPS)
