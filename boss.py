# boss.py
"""El Vacío: el antagonista de Matrixia (GDD sección 11 — "entidad negra de
matrices fracturadas con símbolo 0", personalidad intimidante).

Aparece cada vez que el jugador sube de nivel en cualquier tema: la pantalla se
raja, la partida se oscurece detrás (no desaparece: es una interrupción, no otra
pantalla) y El Vacío se abre encima para burlarse del progreso con una frase al
azar, escrita como a máquina. Más de 60 frases para que no se repita seguido.

Comparte su lenguaje visual con la cinemática de apertura (intro.py), donde es
él quien fractura la Matriz Original: orbe negro, borde carmesí y el 0. La luz
se dibuja con las técnicas de luces.py (resplandores sumados, sin capas alfa
de pantalla completa), porque esto también corre en el navegador.
"""
import asyncio
import math
import random
import sys

import pygame
import pygame.gfxdraw

import entrada
from config import Config
from fuentes import fuente, TITULO, TITULO_SUAVE, TEXTO_FUERTE
from luces import (luz, oscurecer, multiplicar_todo, iluminar_todo, guardado, mezcla,
                   ease, ease_out, ease_out_back, fase)
from ui import draw_button

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


_CX, _CY = Config.ANCHO // 2, 270   # centro de El Vacío
RADIO = 86
CARMESI = (232, 58, 108)
# Color por el que se multiplica la partida al oscurecerla: no un gris (se leía
# como "atenuado") sino un violeta profundo, para que parezca que el vacío se la
# traga y el aura carmesí se lea como luz y no como una mancha rosa.
TINTE_VACIO = (34, 22, 52)

# Margen antes de aceptar clics: El Vacío aparece justo después de la jugada
# que completó el nivel, y ese mismo clic no debe poder cerrarlo al instante.
ESPERA_ANTES_DE_ACEPTAR = 0.6
LETRAS_POR_SEGUNDO = 40


def _envolver_px(fuente_txt, texto_largo, max_width):
    palabras = texto_largo.split()
    if not palabras:
        return []
    lineas, actual = [], palabras[0]
    for palabra in palabras[1:]:
        candidato = actual + ' ' + palabra
        if fuente_txt.size(candidato)[0] <= max_width:
            actual = candidato
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


class _Vacio:
    """El Vacío del lore: "entidad negra de matrices fracturadas con símbolo 0".
    Un orbe negro con el 0, esquirlas de matriz rota orbitando, grietas que
    laten y luz que es absorbida hacia su centro."""

    def __init__(self):
        rng = random.Random()
        self.esquirlas = []
        for _ in range(16):
            n = rng.choice((4, 5))
            tam = rng.uniform(13, 26)
            vertices = [(math.tau * k / n + rng.uniform(-0.35, 0.35), tam * rng.uniform(0.6, 1.0))
                        for k in range(n)]
            self.esquirlas.append({
                'radio': rng.uniform(150, 255), 'fase': rng.uniform(0, math.tau),
                'vel': rng.uniform(0.25, 0.6) * rng.choice((-1, 1)),
                'aplanado': rng.uniform(0.32, 0.5), 'giro': rng.uniform(-1.6, 1.6),
                'vertices': vertices, 'retraso': rng.uniform(0.0, 0.5),
            })
        self.grietas = []
        for k in range(7):
            ang = k * math.tau / 7 + rng.uniform(-0.3, 0.3)
            x = _CX + math.cos(ang) * RADIO
            y = _CY + math.sin(ang) * RADIO
            puntos = [(x, y)]
            for _ in range(rng.randint(5, 8)):
                ang += rng.uniform(-0.5, 0.5)
                largo = rng.uniform(22, 40)
                x += math.cos(ang) * largo
                y += math.sin(ang) * largo
                puntos.append((x, y))
            self.grietas.append(puntos)
        self.absorbidas = []  # partículas de luz que caen hacia el centro

    def _dibujar_esquirla(self, s, e, t, radio_orbita, presencia):
        ang = e['fase'] + t * e['vel']
        x = _CX + math.cos(ang) * radio_orbita
        y = _CY + math.sin(ang) * radio_orbita * e['aplanado']
        giro = t * e['giro']
        escala = presencia * (0.75 + 0.25 * math.sin(ang))  # más chicas al fondo
        puntos = [(x + math.cos(a + giro) * r * escala, y + math.sin(a + giro) * r * escala)
                  for a, r in e['vertices']]
        if escala < 0.08:
            return
        luz(s, x, y, 34 * escala, (150, 20, 60), 0.35 * presencia, curva=2.2, niveles=8)
        pygame.gfxdraw.filled_polygon(s, puntos, (22, 12, 30))
        pygame.gfxdraw.aapolygon(s, puntos, (205, 55, 100))
        # una arista iluminada, como un filo de cristal
        pygame.draw.aaline(s, (255, 170, 200), puntos[0], puntos[1])

    def dibujar(self, s, t, crece, presencia, colapso=0.0):
        """crece: tamaño del orbe (0..1+), presencia: esquirlas y grietas (0..1),
        colapso: al cerrarse, todo se contrae hacia el centro (0..1)."""
        pulso = 0.5 + 0.5 * math.sin(t * 3.1)
        r = RADIO * crece * (1 - colapso)

        # Grietas que laten sobre la partida oscurecida
        for k, puntos in enumerate(self.grietas):
            n = max(1, int(round(min(1.0, presencia * 1.4) * (len(puntos) - 1))))
            tramo = puntos[:n + 1]
            if len(tramo) < 2 or presencia <= 0:
                continue
            brillo = (0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 9 + k * 1.7))) * presencia * (1 - colapso)
            pygame.draw.lines(s, oscurecer((120, 16, 50), brillo), False, tramo, 6)
            pygame.draw.lines(s, oscurecer((255, 120, 165), brillo), False, tramo, 2)

        # Luz absorbida: cae en espiral hacia el centro y se apaga al entrar
        if presencia > 0.3 and colapso == 0 and random.random() < 0.7:
            a = random.uniform(0, math.tau)
            self.absorbidas.append([a, random.uniform(330, 430), random.uniform(0.6, 1.1),
                                    random.choice(((255, 90, 140), (170, 70, 230), (255, 150, 90)))])
        vivas = []
        for p in self.absorbidas:
            p[1] -= (60 + (430 - p[1]) * 1.6) * (1 / 60.0)
            p[0] += p[2] * (1 / 60.0) * 2.2
            if p[1] <= RADIO * 0.9:
                continue
            k = min(1.0, (430 - p[1]) / 90.0) * min(1.0, (p[1] - RADIO) / 70.0)
            luz(s, _CX + math.cos(p[0]) * p[1], _CY + math.sin(p[0]) * p[1] * 0.85,
                6, p[3], k, curva=2.6)
            vivas.append(p)
        self.absorbidas = vivas

        radio_orbita = lambda e: e['radio'] * (1 - colapso) * ease_out(fase(presencia, e['retraso'] * 0.5, 1.0))
        detras = [e for e in self.esquirlas if math.sin(e['fase'] + t * e['vel']) < 0]
        delante = [e for e in self.esquirlas if math.sin(e['fase'] + t * e['vel']) >= 0]
        for e in detras:
            self._dibujar_esquirla(s, e, t, radio_orbita(e), presencia * (1 - colapso))

        if r > 1:
            luz(s, _CX, _CY, r * 3.3, (120, 8, 52), 0.7 + 0.3 * pulso, curva=1.5, niveles=8)
            luz(s, _CX, _CY, r * 1.75, (210, 30, 85), 0.55 + 0.2 * pulso, curva=2.3, niveles=8)
            ri = int(r)
            pygame.gfxdraw.filled_circle(s, _CX, _CY, ri, (7, 3, 12))
            # Remolino interior: arcos violeta que giran y dan profundidad
            for k, (fr, vel) in enumerate(((0.78, 0.9), (0.58, -1.3), (0.4, 1.8))):
                rr = int(r * fr)
                if rr > 4:
                    a0 = t * vel + k * 2.1
                    pygame.draw.arc(s, (64, 18, 58), (_CX - rr, _CY - rr, rr * 2, rr * 2),
                                    a0, a0 + 2.2, 2)
            pygame.gfxdraw.aacircle(s, _CX, _CY, ri, CARMESI)
            pygame.gfxdraw.aacircle(s, _CX, _CY, max(1, ri - 1), (150, 30, 70))
            self._dibujar_cero(s, t, r)

        for e in delante:
            self._dibujar_esquirla(s, e, t, radio_orbita(e), presencia * (1 - colapso))

    def _dibujar_cero(self, s, t, r):
        tam = max(8, int(r * 1.3) // 4 * 4)
        cero = guardado(('vacio_cero', tam), lambda: fuente(TITULO, tam).render("0", True, (255, 96, 128)))
        rect = cero.get_rect(center=(_CX, _CY + 2))
        luz(s, _CX, _CY, r * 0.75, (255, 40, 90), 0.55, curva=2.0, niveles=8)
        # Interferencia: cada ~1,7 s el 0 se descompone en rojo y cian un instante
        if (t % 1.7) < 0.14:
            rojo = guardado(('vacio_cero_r', tam), lambda: fuente(TITULO, tam).render("0", True, (200, 0, 40)))
            cian = guardado(('vacio_cero_c', tam), lambda: fuente(TITULO, tam).render("0", True, (0, 160, 200)))
            s.blit(rojo, rect.move(-7, 0), None, pygame.BLEND_ADD)
            s.blit(cian, rect.move(7, 0), None, pygame.BLEND_ADD)
            corte = pygame.Rect(0, int(rect.height * random.uniform(0.3, 0.6)), rect.width, 10)
            s.blit(cero, rect.move(random.choice((-12, 12)), corte.y).topleft, corte)
        else:
            s.blit(cero, rect)


def _grieta_de_entrada(s, k):
    """La pantalla se raja de lado a lado justo antes de que El Vacío aparezca."""
    if k <= 0 or k >= 1:
        return
    rng = random.Random(3)
    puntos, x = [], 0
    while x <= Config.ANCHO:
        puntos.append((x, _CY + rng.uniform(-26, 26)))
        x += rng.uniform(40, 80)
    color = mezcla((255, 245, 250), (120, 20, 60), k)
    grosor = max(1, int(5 * (1 - k)))
    pygame.draw.lines(s, color, False, puntos, grosor)


async def mostrar_boss(ventana, sound, nivel_completado, tema_nombre):
    """Interrumpe la partida: la pantalla se raja, el juego se oscurece detrás y
    El Vacío se burla del nivel recién superado. Vuelve con 'Continuar'."""
    clock = pygame.time.Clock()
    frase = random.choice(FRASES)
    vacio = _Vacio()

    # La partida queda congelada detrás; su versión oscura se calcula una vez.
    partida = ventana.copy()
    partida_oscura = partida.copy()
    multiplicar_todo(partida_oscura, TINTE_VACIO)

    f_nombre = fuente(TITULO, 26)
    f_frase = fuente(TEXTO_FUERTE, 25)
    f_etiqueta = fuente(TEXTO_FUERTE, 17)

    f_boton = fuente(TITULO_SUAVE, 24)
    ancho_panel = 880
    lineas = _envolver_px(f_frase, frase, ancho_panel - 64)
    # El panel se ajusta al texto (1 a 3 líneas) y queda apoyado sobre el botón,
    # en vez de tener un alto fijo que dejaba un hueco bajo las frases cortas.
    alto_panel = 70 + 36 * len(lineas) + 18
    boton = pygame.Rect(Config.ANCHO // 2 - 130, 694, 260, 56)
    panel = pygame.Rect(Config.ANCHO // 2 - ancho_panel // 2, boton.y - 24 - alto_panel,
                        ancho_panel, alto_panel)
    total_letras = sum(len(l) for l in lineas)

    if sound:
        sound.play('shatter')
    pygame.event.clear()
    t0 = pygame.time.get_ticks() / 1000.0
    t_texto = 1.0           # cuándo empieza a escribirse la frase
    t_salida = None

    while True:
        t = pygame.time.get_ticks() / 1000.0 - t0
        letras = int((t - t_texto) * LETRAS_POR_SEGUNDO) if t >= t_texto else 0
        escrito = letras >= total_letras

        mouse_pos = entrada.posicion_puntero()
        for ev in entrada.obtener_eventos():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if t_salida is not None or t < ESPERA_ANTES_DE_ACEPTAR:
                continue
            pulsa = ev.type == pygame.MOUSEBUTTONDOWN
            tecla = ev.type == pygame.KEYDOWN and ev.key in (
                pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE)
            if not (pulsa or tecla):
                continue
            if not escrito:
                # Primer toque: termina de escribir la frase (no salta nada)
                t_texto = t - total_letras / LETRAS_POR_SEGUNDO - 0.01
            elif tecla or boton.collidepoint(ev.pos):
                t_salida = t

        colapso = ease(fase(t, t_salida, t_salida + 0.45)) if t_salida is not None else 0.0
        if colapso >= 1.0:
            ventana.blit(partida, (0, 0))
            pygame.display.flip()
            return

        # Fondo: la partida, oscureciéndose al entrar y aclarándose al salir
        caida = ease(fase(t, 0.12, 0.75))
        oscuridad = caida * (1 - colapso)
        if oscuridad >= 1.0:
            ventana.blit(partida_oscura, (0, 0))
        else:
            ventana.blit(partida, (0, 0))
            multiplicar_todo(ventana, mezcla((255, 255, 255), TINTE_VACIO, oscuridad))

        _grieta_de_entrada(ventana, fase(t, 0.0, 0.35))
        crece = ease_out_back(fase(t, 0.22, 0.85), 1.6)
        presencia = fase(t, 0.45, 1.25)
        vacio.dibujar(ventana, t, crece, presencia, colapso)

        if t_salida is None:
            k_ui = ease_out(fase(t, 0.7, 1.1))
            etiqueta = guardado(('vacio_etq', nivel_completado, tema_nombre), lambda: f_etiqueta.render(
                "NIVEL %d DE %s SUPERADO" % (nivel_completado, tema_nombre.upper()), True, (236, 176, 196)))
            etiqueta.set_alpha(int(255 * k_ui))
            ventana.blit(etiqueta, etiqueta.get_rect(center=(Config.ANCHO // 2, 54)))

            if k_ui > 0:
                p = panel.move(0, int(40 * (1 - k_ui)))
                luz(ventana, p.centerx, p.centery, p.width // 2 + 40, (110, 10, 45), 0.6 * k_ui,
                    curva=1.6, alto=p.height // 2 + 40, niveles=6)
                pygame.draw.rect(ventana, (17, 9, 23), p, border_radius=18)
                pygame.draw.rect(ventana, (128, 32, 64), p, 2, border_radius=18)
                pygame.draw.line(ventana, CARMESI, (p.x + 28, p.y + 54), (p.x + 120, p.y + 54), 3)
                nombre = guardado('vacio_nombre', lambda: f_nombre.render("EL VACÍO", True, (255, 98, 136)))
                ventana.blit(nombre, (p.x + 28, p.y + 16))

                y = p.y + 70
                restantes = letras
                for linea in lineas:
                    visible = linea[:max(0, restantes)]
                    restantes -= len(linea)
                    if visible:
                        ventana.blit(f_frase.render(visible, True, (246, 234, 238)), (p.x + 32, y))
                    y += 36
                if not escrito and (int(t * 2.5) % 2 == 0):
                    # cursor de máquina de escribir: indica que hay más por leer
                    pygame.draw.rect(ventana, CARMESI, (p.right - 44, p.bottom - 22, 14, 4))

            if escrito:
                draw_button(ventana, boton, "Continuar", mouse_pos, (128, 30, 60), (165, 46, 82),
                            font_obj=f_boton)

        if 0 < colapso < 0.35:
            iluminar_todo(ventana, 0.5 * (1 - colapso / 0.35), color=(255, 200, 220))

        pygame.display.flip()
        clock.tick(Config.FPS)
        await asyncio.sleep(0)
