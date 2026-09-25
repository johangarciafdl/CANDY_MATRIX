# vector_game.py
"""Minijuego del tema Vectores: "Cazavectores". A diferencia de Matrices (un
match-3 sobre una cuadrícula), aquí no hay tablero: el jugador ve un plano
cartesiano con un objetivo (un vector) y una bandeja de vectores sueltos, y debe
elegir DOS que sumados den exactamente ese objetivo. Cada acierto refuerza la
suma de vectores componente a componente; el bonus de ortogonalidad refuerza
el producto punto. Comparte con matrix_game el mismo marco (panel derecho,
cronómetro, habilidades cargables con preguntas, Zona de Estudio y Excel)."""
import math
import random
import time
import pygame

from config import Config, font, font_small, font_large, NEGRO
from ui import draw_right_panel, get_panel_buttons, draw_button, texto, draw_circle_aa, draw_ring_aa
from learn_zone import mostrar_zona_estudio
from excel_exporter import export_to_excel
from quiz_system import pick_question
from matrix_logic import generar_tablero
from skills import SistemaHabilidades
from topics import nombre as nombre_tema
import progress
import lore
import effects

OVERLAY_DURATION = 2.5
DUR_FLOTANTE = 0.9
DUR_AVISO = 4.0
DUR_RESULTADO = 0.9
DUR_RADAR = 3.0

BOTON_REINTENTAR = pygame.Rect(Config.LEFT_WIDTH // 2 - 140, Config.ALTO // 2 + 40, 280, 60)
BOTON_MENU = pygame.Rect(Config.LEFT_WIDTH // 2 - 140, Config.ALTO // 2 + 114, 280, 60)
BOTON_MAPA = pygame.Rect(Config.LEFT_WIDTH // 2 - 140, Config.ALTO // 2 + 60, 280, 60)

PLANO_RECT = pygame.Rect(40, 130, Config.LEFT_WIDTH - 80, 330)
TRAY_Y = PLANO_RECT.bottom + 30
CHIP_ALTO = 72

HABILIDADES_VECTOR = [
    {'id': 'espejo', 'nombre': 'Espejo', 'color': (90, 150, 210),
     'cooldown': 22, 'desc': 'Invierte el signo del vector seleccionado (v -> -v).'},
    {'id': 'amplifica', 'nombre': 'Amplifica', 'color': (215, 145, 60),
     'cooldown': 28, 'desc': 'Duplica las componentes del vector seleccionado (v -> 2v).'},
    {'id': 'radar', 'nombre': 'Radar', 'color': (150, 95, 205),
     'cooldown': 38, 'desc': 'Resalta un par de vectores de la bandeja que sí suman el objetivo.'},
]
_POR_ID_VEC = {h['id']: h for h in HABILIDADES_VECTOR}


def nivel_goal(nivel):
    return Config.GOAL_BASE * nivel


def _rango_componente(nivel):
    return min(4 + nivel, 9)


def _chip_aleatorio(nivel):
    r = _rango_componente(nivel)
    valores = [v for v in range(-r, r + 1) if v != 0]
    return [random.choice(valores), random.choice(valores)]


def _cantidad_chips(nivel):
    return min(5 + nivel // 2, 9)


# -------------------- ICONOS DE HABILIDAD --------------------
def _icono_vector(hid, lado=40):
    s = pygame.Surface((lado, lado), pygame.SRCALPHA)
    c = lado // 2
    r = lado // 2 - 6
    color = _POR_ID_VEC[hid]['color']

    def flecha(surf, origen, fin, color, grosor=3):
        pygame.draw.line(surf, color, origen, fin, grosor)
        dx, dy = fin[0] - origen[0], fin[1] - origen[1]
        ang = pygame.math.Vector2(dx, dy)
        if ang.length() > 0:
            ang = ang.normalize()
            izq = ang.rotate(150) * 8
            der = ang.rotate(-150) * 8
            pygame.draw.polygon(surf, color, [fin, (fin[0] + izq.x, fin[1] + izq.y),
                                              (fin[0] + der.x, fin[1] + der.y)])

    if hid == 'espejo':
        flecha(s, (c, c), (c + r, c - r * 0.4), (240, 240, 240))
        pygame.draw.line(s, (240, 240, 240), (c - r, c + r * 0.2), (c + r, c + r * 0.2), 1)
        flecha(s, (c, c), (c - r, c + r * 0.4), (255, 210, 90))
    elif hid == 'amplifica':
        flecha(s, (c - r * 0.5, c + r * 0.5), (c, c), (240, 240, 240), 2)
        flecha(s, (c, c), (c + r, c - r), color=(255, 210, 90), grosor=4)
    else:  # radar
        for radio in (r, r * 0.65, r * 0.3):
            draw_ring_aa(s, (c, c), radio, 1, (240, 240, 240))
        draw_circle_aa(s, (c, c), 3, (255, 210, 90))
    return s


# -------------------- MODAL DE PREGUNTA PARA CARGAR HABILIDAD --------------------
def _preguntar_para_habilidad(ventana, sound, tema_id, hid):
    habilidad = _POR_ID_VEC[hid]
    tablero_fodder = generar_tablero()
    pregunta = pick_question(tablero_fodder, tema_id)
    entrada = time.time()
    clock = pygame.time.Clock()

    ancho, alto = 760, 420
    rect = pygame.Rect((Config.ANCHO - ancho) // 2, (Config.ALTO - alto) // 2, ancho, alto)
    fase = 'pregunta'
    elegida = None

    while True:
        mouse_pos = pygame.mouse.get_pos()
        opciones_rects = []

        capa = pygame.Surface((Config.ANCHO, Config.ALTO), pygame.SRCALPHA)
        capa.fill((10, 10, 10, 195))
        ventana.blit(capa, (0, 0))

        pygame.draw.rect(ventana, (250, 248, 252), rect, border_radius=18)
        pygame.draw.rect(ventana, habilidad['color'], rect, 5, border_radius=18)

        icono = _icono_vector(hid, 54)
        ventana.blit(icono, icono.get_rect(center=(rect.x + 52, rect.y + 48)))
        ventana.blit(texto(font_large, f"Habilidad: {habilidad['nombre']}", habilidad['color']), (rect.x + 92, rect.y + 26))
        ventana.blit(texto(font_small, habilidad['desc'], (70, 60, 60)), (rect.x + 92, rect.y + 60))

        y = rect.y + 108
        for linea in pregunta['lines']:
            ventana.blit(texto(font_large, linea, (25, 25, 30)), (rect.x + 28, y))
            y += 32

        y += 12
        for idx, opcion in enumerate(pregunta['options']):
            opt_rect = pygame.Rect(rect.x + 40, y, rect.width - 80, 46)
            opciones_rects.append(opt_rect)
            base, hov = (232, 228, 242), (216, 212, 236)
            if fase == 'feedback':
                if idx == pregunta['correct_idx']:
                    base = hov = (168, 220, 168)
                elif idx == elegida:
                    base = hov = (232, 158, 158)
            draw_button(ventana, opt_rect, opcion, mouse_pos, base, hov, text_color=(25, 25, 30))
            y += 54

        boton_cerrar = None
        if fase == 'feedback':
            acierto = elegida == pregunta['correct_idx']
            msg = f"¡Correcto! {habilidad['nombre']} cargada." if acierto else "Incorrecto. La habilidad no se carga."
            ventana.blit(texto(font_large, msg, (30, 130, 45) if acierto else (170, 45, 45)), (rect.x + 28, y + 4))
            boton_cerrar = pygame.Rect(rect.right - 180, rect.bottom - 60, 150, 44)
            draw_button(ventana, boton_cerrar, "Continuar", mouse_pos, (70, 150, 95), (95, 180, 120))

        pygame.display.flip()
        clock.tick(30)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE and fase == 'pregunta':
                return False, time.time() - entrada
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if fase == 'pregunta':
                    for idx, opt_rect in enumerate(opciones_rects):
                        if opt_rect.collidepoint(ev.pos):
                            elegida = idx
                            fase = 'feedback'
                            if sound:
                                sound.play('correct' if idx == pregunta['correct_idx'] else 'error')
                elif boton_cerrar and boton_cerrar.collidepoint(ev.pos):
                    return elegida == pregunta['correct_idx'], time.time() - entrada


# -------------------- JUEGO --------------------
def jugar(ventana, sound, tema_id, estudiante, nivel_inicial=1):
    """Corre partidas de Cazavectores hasta que el jugador vuelve al menú o
    cierra el juego. Devuelve 'menu' o 'salir'."""
    clock = pygame.time.Clock()
    effects.limpiar()
    primera_vez = True

    while True:
        nivel = nivel_inicial
        score = 0
        intentos = 0
        racha = 0
        level_start_time = time.time()
        history = []
        events = []
        flotantes = []
        aviso = None
        running = True

        chips = [_chip_aleatorio(nivel) for _ in range(_cantidad_chips(nivel))]
        seleccionados = []
        fase_combo = 'esperando'  # 'esperando' | 'resultado'
        resultado_ok = False
        resultado_t0 = 0.0
        radar_par = None
        radar_t0 = 0.0

        def nuevo_objetivo():
            i, j = random.sample(range(len(chips)), 2)
            return [chips[i][0] + chips[j][0], chips[i][1] + chips[j][1]]

        objetivo = nuevo_objetivo()

        habilidades = SistemaHabilidades(HABILIDADES_VECTOR)
        usos_habilidad = {h['id']: 0 for h in HABILIDADES_VECTOR}

        estado_juego = "jugando"  # "jugando" | "nivel_completo" | "tiempo_agotado"
        overlay_start = 0.0

        if primera_vez:
            frase_entrada = lore.frase(tema_id, 'entrada')
            if frase_entrada:
                aviso = {'texto': frase_entrada, 't0': time.time(), 'color': (60, 110, 170)}
            primera_vez = False

        def agregar_flotante(txt, x, y, color=(255, 242, 170)):
            flotantes.append({'texto': txt, 'x': x, 'y': y,
                              't0': pygame.time.get_ticks() / 1000.0, 'color': color})

        def mostrar_aviso(mensaje, color=(56, 132, 86)):
            nonlocal aviso
            aviso = {'texto': mensaje, 't0': time.time(), 'color': color}

        def pausar_reloj(segundos):
            nonlocal level_start_time
            if segundos:
                level_start_time += segundos
                habilidades.posponer_enfriamientos(segundos)

        def stats_de_chips():
            vals = [v for chip in chips for v in chip]
            if not vals:
                return {'sum': 0, 'min': 0, 'max': 0, 'mean': 0}
            return {'sum': sum(vals), 'min': min(vals), 'max': max(vals), 'mean': sum(vals) / len(vals)}

        def guardar_reporte(avisar=False):
            resumen = {_POR_ID_VEC[hid]['nombre']: veces for hid, veces in usos_habilidad.items() if veces}
            ruta, error = export_to_excel(nivel, score, intentos, history, events,
                                          stats_de_chips(), resumen, nombre_tema(tema_id))
            if ruta:
                events.append(f"Reporte exportado: {ruta}")
                if avisar:
                    import os
                    mostrar_aviso(f"Excel guardado: {os.path.basename(ruta)}", (56, 132, 86))
            elif avisar:
                mostrar_aviso(error or "No se pudo exportar el Excel.", (168, 58, 52))

        def evaluar_combo():
            nonlocal score, intentos, racha, fase_combo, resultado_ok, resultado_t0, objetivo
            i1, i2 = seleccionados
            u, v = chips[i1], chips[i2]
            suma = [u[0] + v[0], u[1] + v[1]]
            intentos += 1
            acierto = suma == objetivo

            fase_combo = 'resultado'
            resultado_ok = acierto
            resultado_t0 = time.time()

            cx = PLANO_RECT.centerx
            cy = PLANO_RECT.y + 30
            if acierto:
                racha += 1
                ortogonal = (u[0] * v[0] + u[1] * v[1]) == 0
                puntos = 35 + 10 * racha + (20 if ortogonal else 0)
                score += puntos
                sound.play('explosion')
                color_burst = (255, 200, 90) if ortogonal else (200, 255, 200)
                effects.spawn_burst(cx, cy, color_burst, cantidad=10 + 2 * racha)
                desc = f"u={tuple(u)} + v={tuple(v)} = {tuple(suma)} = objetivo (+{puntos} pts, racha x{racha})"
                if ortogonal:
                    desc += " | ¡Bonus! u·v = 0: son ortogonales"
                events.append(desc)
                history.append({'matriz': [list(u), list(v)], 'evento': desc})
                agregar_flotante(f"+{puntos}" + (" ⟂" if ortogonal else ""), cx, cy, (200, 255, 200))
                for idx in (i1, i2):
                    chips[idx] = _chip_aleatorio(nivel)
                objetivo = nuevo_objetivo()
            else:
                racha = 0
                sound.play('error')
                agregar_flotante("No coincide", cx, cy, (255, 210, 210))

        def usar_habilidad(hid):
            nonlocal radar_par, radar_t0
            if hid in ('espejo', 'amplifica'):
                if len(seleccionados) != 1:
                    mostrar_aviso("Selecciona un solo vector de la bandeja primero.", (150, 120, 40))
                    return
                idx = seleccionados[0]
                if hid == 'espejo':
                    chips[idx] = [-chips[idx][0], -chips[idx][1]]
                else:
                    chips[idx] = [chips[idx][0] * 2, chips[idx][1] * 2]
                habilidades.consumir(hid)
                usos_habilidad[hid] += 1
                events.append(f"Habilidad {_POR_ID_VEC[hid]['nombre']} usada sobre el vector de la bandeja {idx + 1}")
            else:  # radar
                par = None
                for a in range(len(chips)):
                    for b in range(a + 1, len(chips)):
                        if [chips[a][0] + chips[b][0], chips[a][1] + chips[b][1]] == objetivo:
                            par = (a, b)
                            break
                    if par:
                        break
                if par:
                    radar_par = par
                    radar_t0 = time.time()
                    habilidades.consumir(hid)
                    usos_habilidad[hid] += 1
                    events.append("Habilidad Radar usada: reveló un par que suma el objetivo")
                else:
                    mostrar_aviso("Ningún par de la bandeja suma el objetivo ahora mismo.", (150, 120, 40))

        def manejar_click_habilidad(hid):
            estado = habilidades.estado_de(hid)
            if estado == 'limite':
                mostrar_aviso(f"Ya gastaste las {Config.MAX_SKILL_USES_PER_LEVEL} habilidades de este nivel.", (168, 58, 52))
            elif estado == 'enfriando':
                mostrar_aviso(f"{_POR_ID_VEC[hid]['nombre']} se recarga en {int(habilidades.segundos_restantes(hid)) + 1}s.",
                              (150, 120, 40))
            elif estado == 'lista':
                usar_habilidad(hid)
            else:
                acierto, pausa = _preguntar_para_habilidad(ventana, sound, tema_id, hid)
                pausar_reloj(pausa)
                if acierto:
                    habilidades.otorgar(hid)
                    mostrar_aviso(f"¡{_POR_ID_VEC[hid]['nombre']} cargada! Vuelve a pulsarla para usarla.", (56, 132, 86))
                else:
                    mostrar_aviso("Respuesta incorrecta: la habilidad no se cargó.", (168, 58, 52))

        # ---------- Layout de bandeja y barra de habilidades ----------
        def rects_chips():
            n = len(chips)
            gap = 14
            ancho = min(96, (PLANO_RECT.width - gap * (n - 1)) // max(1, n))
            total = n * ancho + (n - 1) * gap
            x0 = PLANO_RECT.x + (PLANO_RECT.width - total) // 2
            return [pygame.Rect(x0 + k * (ancho + gap), TRAY_Y, ancho, CHIP_ALTO) for k in range(n)]

        def rects_habilidades():
            ancho, alto, gap = 150, 70, 18
            total = len(HABILIDADES_VECTOR) * ancho + (len(HABILIDADES_VECTOR) - 1) * gap
            x0 = PLANO_RECT.x + (PLANO_RECT.width - total) // 2
            y = TRAY_Y + CHIP_ALTO + 26
            return {h['id']: pygame.Rect(x0 + k * (ancho + gap), y, ancho, alto)
                    for k, h in enumerate(HABILIDADES_VECTOR)}

        def escala_plano():
            radio_max = max(3, max(abs(v) for chip in (chips + [objetivo]) for v in chip))
            return min(PLANO_RECT.width, PLANO_RECT.height) / (2.4 * radio_max)

        def punto_plano(vec, escala):
            cx, cy = PLANO_RECT.center
            return int(cx + vec[0] * escala), int(cy - vec[1] * escala)

        def dibujar_plano():
            pygame.draw.rect(ventana, (255, 255, 255), PLANO_RECT, border_radius=12)
            if fase_combo == 'resultado':
                color_borde = (110, 190, 120) if resultado_ok else (210, 90, 90)
                pygame.draw.rect(ventana, color_borde, PLANO_RECT, 4, border_radius=12)
            else:
                pygame.draw.rect(ventana, (210, 190, 175), PLANO_RECT, 2, border_radius=12)
            cx, cy = PLANO_RECT.center
            pygame.draw.line(ventana, (215, 210, 220), (PLANO_RECT.x + 10, cy), (PLANO_RECT.right - 10, cy), 1)
            pygame.draw.line(ventana, (215, 210, 220), (cx, PLANO_RECT.y + 10), (cx, PLANO_RECT.bottom - 10), 1)

            escala = escala_plano()
            fin = punto_plano(objetivo, escala)
            fin_v = pygame.math.Vector2(fin)
            color_objetivo = (233, 90, 64)
            pygame.draw.line(ventana, color_objetivo, (cx, cy), fin, 4)
            direccion = fin_v - pygame.math.Vector2(cx, cy)
            if direccion.length() > 0:
                direccion = direccion.normalize()
                izq = fin_v - direccion.rotate(150) * 14
                der = fin_v - direccion.rotate(-150) * 14
                pygame.draw.polygon(ventana, color_objetivo, [fin_v, izq, der])
            draw_circle_aa(ventana, (cx, cy), 4, color_objetivo)
            ventana.blit(texto(font_small, f"Objetivo: {tuple(objetivo)}", color_objetivo),
                         (PLANO_RECT.x + 10, PLANO_RECT.y + 8))

        def dibujar_chips():
            rects = rects_chips()
            radar_activo = radar_par and (time.time() - radar_t0) < DUR_RADAR
            en_fallo = fase_combo == 'resultado' and not resultado_ok
            t_fallo = (time.time() - resultado_t0) if en_fallo else 0.0
            for idx, (chip, rect) in enumerate(zip(chips, rects)):
                seleccionado = idx in seleccionados
                en_radar = radar_activo and idx in radar_par
                if en_fallo and seleccionado:
                    # Sacudida corta + tinte rojo: el error necesitaba señal
                    # visual propia, no solo sonido y texto flotante.
                    amortiguacion = max(0.0, 1 - t_fallo / DUR_RESULTADO)
                    dx = int(5 * math.sin(t_fallo * 45) * amortiguacion)
                    rect = rect.move(dx, 0)
                    base, borde = (255, 205, 200), (200, 70, 60)
                else:
                    base = (255, 226, 140) if en_radar else ((200, 230, 255) if seleccionado else (240, 236, 230))
                    borde = (255, 180, 40) if en_radar else ((60, 130, 210) if seleccionado else (190, 180, 170))
                pygame.draw.rect(ventana, tuple(int(c * 0.7) for c in base), rect.move(0, 3), border_radius=12)
                pygame.draw.rect(ventana, base, rect, border_radius=12)
                pygame.draw.rect(ventana, borde, rect, 3 if (seleccionado or en_radar or en_fallo) else 2,
                                 border_radius=12)
                etiqueta = texto(font, f"({chip[0]}, {chip[1]})", (35, 30, 25))
                ventana.blit(etiqueta, etiqueta.get_rect(center=rect.center))

        def dibujar_barra_habilidades(mouse_pos):
            rects = rects_habilidades()
            restantes = max(0, Config.MAX_SKILL_USES_PER_LEVEL - habilidades.usos_nivel)
            primer = rects[HABILIDADES_VECTOR[0]['id']]
            ventana.blit(texto(font_small, f"Habilidades  ·  usos restantes en el nivel: {restantes}", (92, 52, 36)),
                         (primer.x, primer.y - 22))
            for h in HABILIDADES_VECTOR:
                hid = h['id']
                rect = rects[hid]
                estado = habilidades.estado_de(hid)
                if estado == 'limite':
                    base, etiqueta = (150, 140, 135), "Límite"
                elif estado == 'enfriando':
                    base, etiqueta = (128, 128, 140), f"{int(habilidades.segundos_restantes(hid)) + 1}s"
                elif estado == 'lista':
                    base, etiqueta = h['color'], "¡Lista!"
                else:
                    base, etiqueta = tuple(int(c * 0.55) for c in h['color']), "Responder"
                hover = h['color'] if rect.collidepoint(mouse_pos) else base
                pygame.draw.rect(ventana, tuple(int(c * 0.5) for c in base), rect.move(0, 3), border_radius=12)
                pygame.draw.rect(ventana, hover, rect, border_radius=12)
                pygame.draw.rect(ventana, (255, 226, 90) if estado == 'lista' else (255, 255, 255), rect,
                                 3, border_radius=12)
                icono = _icono_vector(hid, 32)
                ventana.blit(icono, icono.get_rect(center=(rect.x + 26, rect.centery)))
                ventana.blit(texto(font_small, h['nombre'], (255, 255, 255)), (rect.x + 48, rect.y + 12))
                ventana.blit(texto(font_small, etiqueta, (255, 255, 255)), (rect.x + 48, rect.y + 34))

        def dibujar_flotantes():
            ahora = pygame.time.get_ticks() / 1000.0
            vivos = []
            for f in flotantes:
                t = (ahora - f['t0']) / DUR_FLOTANTE
                if t >= 1.0:
                    continue
                vivos.append(f)
                alpha = int(255 * (1 - t))
                pos = (f['x'], int(f['y'] - 45 * t))
                sombra = font_large.render(f['texto'], True, (70, 35, 20))
                frente = font_large.render(f['texto'], True, f['color'])
                sombra.set_alpha(alpha)
                frente.set_alpha(alpha)
                ventana.blit(sombra, sombra.get_rect(center=(pos[0] + 2, pos[1] + 2)))
                ventana.blit(frente, frente.get_rect(center=pos))
            flotantes[:] = vivos

        def dibujar_aviso():
            if not aviso:
                return
            t = time.time() - aviso['t0']
            if t > DUR_AVISO:
                return
            contenido = font.render(aviso['texto'], True, (255, 255, 255))
            rect = pygame.Rect(0, 0, contenido.get_width() + 44, 46)
            rect.center = (Config.LEFT_WIDTH // 2, 52)
            capa = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(capa, (*aviso['color'], 240), capa.get_rect(), border_radius=13)
            pygame.draw.rect(capa, (255, 255, 255, 240), capa.get_rect(), 2, border_radius=13)
            capa.blit(contenido, contenido.get_rect(center=(rect.width // 2, rect.height // 2)))
            if t > DUR_AVISO - 0.7:
                capa.set_alpha(int(255 * (DUR_AVISO - t) / 0.7))
            ventana.blit(capa, rect.topleft)

        def dibujar_texto_central(titulo, sub=None, frase=None):
            render = font_large.render(titulo, True, NEGRO)
            ventana.blit(render, render.get_rect(center=(Config.LEFT_WIDTH // 2, Config.ALTO // 2)))
            if sub:
                render2 = font.render(sub, True, NEGRO)
                ventana.blit(render2, render2.get_rect(center=(Config.LEFT_WIDTH // 2, Config.ALTO // 2 + 40)))
            if frase:
                render3 = font_small.render(f'{lore.continente(tema_id)["guardian"]}: "{frase}"', True, (80, 55, 30))
                ventana.blit(render3, render3.get_rect(center=(Config.LEFT_WIDTH // 2, Config.ALTO // 2 + 74)))

        # ---------- Bucle de la partida ----------
        while running:
            tiempo_restante = max(0, Config.LEVEL_TIME - (time.time() - level_start_time))

            if fase_combo == 'resultado' and (time.time() - resultado_t0) >= DUR_RESULTADO:
                seleccionados = []
                fase_combo = 'esperando'

            if estado_juego == "jugando" and score >= nivel_goal(nivel):
                guardar_reporte()
                progress.registrar_resultado(estudiante, tema_id, nivel, score)
                progress.desbloquear_nivel(estudiante, tema_id, nivel)
                sound.play('levelup')
                effects.spawn_confetti(pygame.Rect(0, 0, Config.LEFT_WIDTH, 40))
                estado_juego = "modulo_completo" if nivel >= Config.MAX_LEVEL else "nivel_completo"
                overlay_start = time.time()
            elif estado_juego == "jugando" and tiempo_restante <= 0:
                guardar_reporte()
                progress.registrar_resultado(estudiante, tema_id, nivel, score)
                estado_juego = "tiempo_agotado"
                overlay_start = time.time()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if estado_juego == "jugando":
                        guardar_reporte()
                        progress.registrar_resultado(estudiante, tema_id, nivel, score)
                    return 'salir'

                elif event.type == pygame.MOUSEBUTTONDOWN and estado_juego == "jugando":
                    mx, my = event.pos

                    rects_hab = rects_habilidades()
                    golpe_hab = next((hid for hid, r in rects_hab.items() if r.collidepoint(mx, my)), None)
                    if golpe_hab:
                        manejar_click_habilidad(golpe_hab)
                    elif mx < Config.LEFT_WIDTH and fase_combo == 'esperando':
                        for idx, rect in enumerate(rects_chips()):
                            if rect.collidepoint(mx, my):
                                if idx in seleccionados:
                                    seleccionados.remove(idx)
                                elif len(seleccionados) < 2:
                                    seleccionados.append(idx)
                                if len(seleccionados) == 2:
                                    evaluar_combo()
                                break
                    elif mx >= Config.LEFT_WIDTH:
                        botones = get_panel_buttons()
                        if botones["estudio"].collidepoint(mx, my):
                            pausar_reloj(mostrar_zona_estudio(ventana, generar_tablero(), sound, tema_id))
                        elif botones["excel"].collidepoint(mx, my):
                            guardar_reporte(avisar=True)
                        elif botones["menu"].collidepoint(mx, my):
                            guardar_reporte()
                            progress.registrar_resultado(estudiante, tema_id, nivel, score)
                            return 'menu'

                elif event.type == pygame.KEYDOWN and estado_juego == "jugando":
                    if event.key == pygame.K_ESCAPE:
                        pausar_reloj(mostrar_zona_estudio(ventana, generar_tablero(), sound, tema_id))

                elif event.type == pygame.MOUSEBUTTONDOWN and estado_juego == "tiempo_agotado":
                    mx, my = event.pos
                    if BOTON_REINTENTAR.collidepoint(mx, my):
                        running = False
                    elif BOTON_MENU.collidepoint(mx, my):
                        return 'menu'

                elif event.type == pygame.MOUSEBUTTONDOWN and estado_juego == "modulo_completo":
                    if BOTON_MAPA.collidepoint(event.pos):
                        return 'menu'

            # ---------- Dibujo ----------
            ventana.fill((247, 233, 214))
            ventana.blit(texto(font_large, "Cazavectores", (150, 90, 40)), (40, 60))
            ventana.blit(texto(font_small, "Elige dos vectores de la bandeja cuya suma sea el objetivo.",
                               (110, 80, 50)), (40, 100))
            dibujar_plano()
            dibujar_chips()
            dibujar_barra_habilidades(pygame.mouse.get_pos())
            dibujar_flotantes()
            effects.update_and_draw(ventana, 1.0 / Config.FPS)
            dibujar_aviso()

            draw_right_panel(ventana, nivel, score, intentos, tiempo_restante,
                             goal=nivel_goal(nivel), tablero=None, mostrar_matriz=False,
                             tema_nombre=nombre_tema(tema_id))

            if estado_juego == "nivel_completo":
                overlay = pygame.Surface((Config.LEFT_WIDTH, Config.ALTO), pygame.SRCALPHA)
                overlay.fill((10, 10, 10, 160))
                ventana.blit(overlay, (0, 0))
                dibujar_texto_central("¡Nivel superado!", f"Nivel {nivel} completado con {score} puntos",
                                      frase=lore.frase(tema_id, 'nivel'))

                if time.time() - overlay_start >= OVERLAY_DURATION:
                    nivel += 1
                    score = 0
                    intentos = 0
                    racha = 0
                    chips = [_chip_aleatorio(nivel) for _ in range(_cantidad_chips(nivel))]
                    objetivo = nuevo_objetivo()
                    seleccionados = []
                    fase_combo = 'esperando'
                    habilidades.reiniciar_nivel()
                    level_start_time = time.time()
                    estado_juego = "jugando"
                    flotantes.clear()

            elif estado_juego == "tiempo_agotado":
                overlay = pygame.Surface((Config.LEFT_WIDTH, Config.ALTO), pygame.SRCALPHA)
                overlay.fill((10, 10, 10, 170))
                ventana.blit(overlay, (0, 0))
                dibujar_texto_central("¡Se acabó el tiempo!", f"Nivel {nivel} — {score}/{nivel_goal(nivel)} puntos",
                                      frase=lore.frase(tema_id, 'tiempo_agotado'))

                mouse_pos = pygame.mouse.get_pos()
                draw_button(ventana, BOTON_REINTENTAR, "Jugar de nuevo", mouse_pos, (60, 150, 90), (80, 180, 110))
                draw_button(ventana, BOTON_MENU, "Menú principal", mouse_pos, (60, 110, 170), (90, 145, 200))

            elif estado_juego == "modulo_completo":
                overlay = pygame.Surface((Config.LEFT_WIDTH, Config.ALTO), pygame.SRCALPHA)
                overlay.fill((10, 10, 10, 175))
                ventana.blit(overlay, (0, 0))
                dibujar_texto_central(f"¡{nombre_tema(tema_id)} completado!",
                                      f"Superaste los {Config.MAX_LEVEL} niveles con {score} puntos",
                                      frase=lore.frase(tema_id, 'nivel'))
                draw_button(ventana, BOTON_MAPA, "Volver al mapa de niveles", pygame.mouse.get_pos(),
                           (60, 150, 90), (80, 180, 110))

            pygame.display.flip()
            clock.tick(Config.FPS)
