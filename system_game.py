# system_game.py
"""Minijuego del tema Sistemas de ecuaciones: "Cazaecuaciones". Tercera mecánica
distinta del Hub (match-3 en Matrices, combinar vectores en Vectores): aquí no
hay tablero ni plano, hay dos ecuaciones-carta y el jugador debe encontrar el
multiplicador k tal que Fila B + k·Fila A elimine una incógnita — el paso
central de la eliminación gaussiana, hecho jugable. Comparte con los otros
temas el mismo marco: panel derecho, cronómetro, habilidades cargables con
preguntas, Zona de Estudio y exportación a Excel."""
import entrada
import asyncio
import math
import random
import time
import pygame

from config import Config, font, font_small, font_large, NEGRO
from ui import draw_right_panel, get_panel_buttons, draw_button, texto, draw_circle_aa, draw_ring_aa
from learn_zone import mostrar_zona_estudio
from excel_exporter import export_to_excel
from quiz_system import pick_question, generar_sistema_2x2, _formatea_ecuacion
from matrix_logic import generar_tablero
from skills import SistemaHabilidades, modal_pregunta
from topics import nombre as nombre_tema
import progress
import lore
import effects
from boss import mostrar_boss

OVERLAY_DURATION = 2.5
DUR_FLOTANTE = 0.9
DUR_AVISO = 4.0
DUR_RESULTADO = 1.1
DUR_HINT = 3.0

BOTON_REINTENTAR = pygame.Rect(Config.LEFT_WIDTH // 2 - 140, Config.ALTO // 2 + 40, 280, 60)
BOTON_MENU = pygame.Rect(Config.LEFT_WIDTH // 2 - 140, Config.ALTO // 2 + 114, 280, 60)
BOTON_MAPA = pygame.Rect(Config.LEFT_WIDTH // 2 - 140, Config.ALTO // 2 + 60, 280, 60)

CARD_A = pygame.Rect(60, 130, Config.LEFT_WIDTH - 120, 90)
CARD_B = pygame.Rect(60, 236, Config.LEFT_WIDTH - 120, 90)
PREVIEW_RECT = pygame.Rect(60, 340, Config.LEFT_WIDTH - 120, 70)
K_RECT = pygame.Rect(60, 424, Config.LEFT_WIDTH - 120, 56)
BOTON_APLICAR = pygame.Rect(Config.LEFT_WIDTH - 220, 494, 160, 46)
K_MENOS = pygame.Rect(60, 424, 50, 56)
K_MAS = pygame.Rect(60 + (Config.LEFT_WIDTH - 120) - 50, 424, 50, 56)

HABILIDADES_SISTEMAS = [
    {'id': 'escala', 'nombre': 'Escala', 'color': (215, 145, 60),
     'cooldown': 26, 'desc': 'Multiplica la ecuación seleccionada por el factor k actual.'},
    {'id': 'intercambio', 'nombre': 'Intercambio', 'color': (90, 150, 210),
     'cooldown': 20, 'desc': 'Intercambia el orden de las ecuaciones A y B.'},
    {'id': 'revela_k', 'nombre': 'Revela k', 'color': (150, 95, 205),
     'cooldown': 36, 'desc': 'Muestra un valor de k que sí elimina una incógnita.'},
]
_POR_ID_SIS = {h['id']: h for h in HABILIDADES_SISTEMAS}


def nivel_goal(nivel):
    return Config.GOAL_BASE * nivel


def _rango_nivel(nivel):
    return min(2 + nivel, 6)


def _icono_sistema(hid, lado=40):
    s = pygame.Surface((lado, lado), pygame.SRCALPHA)
    c = lado // 2
    r = lado // 2 - 6
    if hid == 'escala':
        pygame.draw.line(s, (240, 240, 240), (c - r, c + r * 0.6), (c + r, c - r * 0.6), 3)
        draw_circle_aa(s, (int(c + r * 0.7), int(c - r * 0.7)), 5, (255, 210, 90))
    elif hid == 'intercambio':
        pygame.draw.line(s, (240, 240, 240), (c - r, c - r * 0.3), (c + r, c - r * 0.3), 3)
        pygame.draw.polygon(s, (240, 240, 240), [(c + r, c - r * 0.3 - 6), (c + r, c - r * 0.3 + 6), (c + r + 8, c - r * 0.3)])
        pygame.draw.line(s, (255, 210, 90), (c - r, c + r * 0.3), (c + r, c + r * 0.3), 3)
        pygame.draw.polygon(s, (255, 210, 90), [(c - r, c + r * 0.3 - 6), (c - r, c + r * 0.3 + 6), (c - r - 8, c + r * 0.3)])
    else:  # revela_k
        for radio in (r, r * 0.6):
            draw_ring_aa(s, (c, c), radio, 1, (240, 240, 240))
        draw_circle_aa(s, (c, c), 4, (255, 210, 90))
    return s


async def _preguntar_para_habilidad(ventana, sound, tema_id, hid):
    """Pregunta para ganar una habilidad de este tema. La ventana es la
    misma de los tres minijuegos (skills.modal_pregunta); aquí solo se elige
    la habilidad, su icono y una pregunta del tema."""
    return await modal_pregunta(ventana, _POR_ID_SIS[hid], _icono_sistema(hid, 56),
                                pick_question(generar_tablero(), tema_id), sound)


async def jugar(ventana, sound, tema_id, estudiante, nivel_inicial=1):
    """Corre partidas de Cazaecuaciones hasta que el jugador vuelve al menú o
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

        fila_a, fila_b, solucion = generar_sistema_2x2(_rango_nivel(nivel))
        k = 1
        fila_activa = 'b'  # cuál carta está seleccionada para Escala/Intercambio
        fase = 'esperando'  # 'esperando' | 'resultado'
        resultado_ok = False
        resultado_t0 = 0.0
        hint_k = None
        hint_t0 = 0.0

        habilidades = SistemaHabilidades(HABILIDADES_SISTEMAS)
        usos_habilidad = {h['id']: 0 for h in HABILIDADES_SISTEMAS}

        estado_juego = "jugando"
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

        def preview_combinada():
            return (fila_b[0] + k * fila_a[0], fila_b[1] + k * fila_a[1], fila_b[2] + k * fila_a[2])

        def stats_de_sistema():
            vals = list(fila_a) + list(fila_b)
            return {'sum': sum(vals), 'min': min(vals), 'max': max(vals), 'mean': sum(vals) / len(vals)}

        def guardar_reporte(avisar=False):
            resumen = {_POR_ID_SIS[hid]['nombre']: veces for hid, veces in usos_habilidad.items() if veces}
            ruta, error = export_to_excel(nivel, score, intentos, history, events,
                                          stats_de_sistema(), resumen, nombre_tema(tema_id))
            if ruta:
                events.append(f"Reporte exportado: {ruta}")
                if avisar:
                    import os
                    mostrar_aviso(f"Excel guardado: {os.path.basename(ruta)}", (56, 132, 86))
            elif avisar:
                mostrar_aviso(error or "No se pudo exportar el Excel.", (168, 58, 52))

        def nuevo_sistema():
            nonlocal fila_a, fila_b, solucion, k, fila_activa
            fila_a, fila_b, solucion = generar_sistema_2x2(_rango_nivel(nivel))
            k = 1
            fila_activa = 'b'

        def aplicar_combinacion():
            nonlocal score, intentos, racha, fase, resultado_ok, resultado_t0, fila_a, fila_b
            intentos += 1
            nueva = preview_combinada()
            nx, ny, nc = nueva

            if k == 0 or (nx != 0 and ny != 0) or (nx == 0 and ny == 0):
                fase, resultado_ok, resultado_t0 = 'resultado', False, time.time()
                racha = 0
                sound.play('error')
                motivo = "k no puede ser 0." if k == 0 else "Esa combinación no elimina ninguna incógnita."
                mostrar_aviso(motivo, (150, 120, 40))
                agregar_flotante("Sin eliminación", CARD_B.centerx, CARD_B.centery, (255, 210, 210))
                return

            variable_eliminada = 'x' if nx == 0 else 'y'

            racha += 1
            bonus_k = 15 if abs(k) == 1 else 0
            puntos = 40 + 15 * racha + bonus_k
            score += puntos
            sound.play('explosion')
            effects.spawn_burst(CARD_B.centerx, CARD_B.centery, (150, 220, 160), cantidad=10 + 2 * racha)

            valor_var, valor_val = ('y', solucion[1]) if variable_eliminada == 'x' else ('x', solucion[0])
            desc = (f"Fila B + ({k})·Fila A elimina {variable_eliminada}: "
                    f"{_formatea_ecuacion(nueva)}  ->  {valor_var}={round(valor_val, 2)} "
                    f"(+{puntos} pts, racha x{racha})")
            events.append(desc)
            history.append({'matriz': [list(fila_a), list(fila_b)], 'evento': desc})

            fase, resultado_ok, resultado_t0 = 'resultado', True, time.time()
            agregar_flotante(f"+{puntos}", CARD_B.centerx, CARD_B.centery, (200, 255, 200))
            mostrar_aviso(f"¡Sistema resuelto! x={solucion[0]}, y={solucion[1]}", (56, 132, 86))

        def usar_habilidad(hid):
            nonlocal hint_k, hint_t0, fila_a, fila_b, fila_activa
            if hid == 'escala':
                if fila_activa == 'a':
                    fila_a = (fila_a[0] * k, fila_a[1] * k, fila_a[2] * k)
                else:
                    fila_b = (fila_b[0] * k, fila_b[1] * k, fila_b[2] * k)
                habilidades.consumir(hid)
                usos_habilidad[hid] += 1
                events.append(f"Habilidad Escala usada: Fila {fila_activa.upper()} ×= {k}")
            elif hid == 'intercambio':
                fila_a, fila_b = fila_b, fila_a
                habilidades.consumir(hid)
                usos_habilidad[hid] += 1
                events.append("Habilidad Intercambio usada: se intercambiaron las filas A y B")
            else:  # revela_k
                encontrado = None
                for cand in range(-6, 7):
                    if cand == 0:
                        continue
                    nx = fila_b[0] + cand * fila_a[0]
                    ny = fila_b[1] + cand * fila_a[1]
                    if (nx == 0) != (ny == 0):
                        encontrado = cand
                        break
                if encontrado is not None:
                    hint_k = encontrado
                    hint_t0 = time.time()
                    habilidades.consumir(hid)
                    usos_habilidad[hid] += 1
                    events.append(f"Habilidad Revela k usada: sugiere k={encontrado}")
                else:
                    mostrar_aviso("No hay un k entero entre -6 y 6 que elimine una incógnita.", (150, 120, 40))

        async def manejar_click_habilidad(hid):
            estado = habilidades.estado_de(hid)
            if estado == 'limite':
                mostrar_aviso(f"Ya gastaste las {Config.MAX_SKILL_USES_PER_LEVEL} habilidades de este nivel.", (168, 58, 52))
            elif estado == 'enfriando':
                mostrar_aviso(f"{_POR_ID_SIS[hid]['nombre']} se recarga en {int(habilidades.segundos_restantes(hid)) + 1}s.",
                              (150, 120, 40))
            elif estado == 'lista':
                usar_habilidad(hid)
            else:
                acierto, pausa = await _preguntar_para_habilidad(ventana, sound, tema_id, hid)
                pausar_reloj(pausa)
                if acierto:
                    habilidades.otorgar(hid)
                    mostrar_aviso(f"¡{_POR_ID_SIS[hid]['nombre']} cargada! Vuelve a pulsarla para usarla.", (56, 132, 86))
                else:
                    mostrar_aviso("Respuesta incorrecta: la habilidad no se cargó.", (168, 58, 52))

        def rects_habilidades():
            ancho, alto, gap = 150, 66, 18
            total = len(HABILIDADES_SISTEMAS) * ancho + (len(HABILIDADES_SISTEMAS) - 1) * gap
            x0 = CARD_A.x + (CARD_A.width - total) // 2
            y = BOTON_APLICAR.bottom + 24
            return {h['id']: pygame.Rect(x0 + i * (ancho + gap), y, ancho, alto)
                    for i, h in enumerate(HABILIDADES_SISTEMAS)}

        def dibujar_carta(rect, fila, etiqueta, activa):
            en_fallo = fase == 'resultado' and not resultado_ok
            if en_fallo:
                # Sacudida corta + tinte rojo: el error necesitaba señal
                # visual propia, no solo sonido y texto flotante.
                t_fallo = time.time() - resultado_t0
                amortiguacion = max(0.0, 1 - t_fallo / DUR_RESULTADO)
                dx = int(5 * math.sin(t_fallo * 45) * amortiguacion)
                rect = rect.move(dx, 0)
                base, borde = (255, 210, 205), (200, 70, 60)
            else:
                base = (232, 244, 255) if activa else (245, 240, 232)
                borde = (60, 130, 210) if activa else (200, 190, 180)
            pygame.draw.rect(ventana, tuple(int(c * 0.85) for c in base), rect.move(0, 3), border_radius=14)
            pygame.draw.rect(ventana, base, rect, border_radius=14)
            pygame.draw.rect(ventana, borde, rect, 3 if (activa or en_fallo) else 2, border_radius=14)
            ventana.blit(texto(font_small, f"Ecuación {etiqueta}", (110, 90, 70)), (rect.x + 16, rect.y + 8))
            ventana.blit(texto(font_large, _formatea_ecuacion(fila), (30, 25, 20)), (rect.x + 16, rect.y + 34))

        def dibujar_preview():
            pygame.draw.rect(ventana, (255, 250, 235), PREVIEW_RECT, border_radius=12)
            pygame.draw.rect(ventana, (220, 200, 150), PREVIEW_RECT, 2, border_radius=12)
            nx, ny, nc = preview_combinada()
            partes = f"{nx}x + {ny}y = {nc}".replace("+ -", "- ")
            color_x = (40, 160, 70) if nx == 0 else (40, 30, 20)
            color_y = (40, 160, 70) if ny == 0 else (40, 30, 20)
            ventana.blit(texto(font_small, f"Vista previa de Fila B + {k}·Fila A:", (140, 100, 40)),
                         (PREVIEW_RECT.x + 16, PREVIEW_RECT.y + 8))
            seg_x = texto(font_large, f"{nx}x", color_x)
            seg_mas = texto(font_large, " + ", (40, 30, 20))
            seg_y = texto(font_large, f"{ny}y", color_y)
            seg_igual = texto(font_large, f" = {nc}", (40, 30, 20))
            x = PREVIEW_RECT.x + 16
            y = PREVIEW_RECT.y + 32
            for seg in (seg_x, seg_mas, seg_y, seg_igual):
                ventana.blit(seg, (x, y))
                x += seg.get_width()

        def dibujar_selector_k(mouse_pos):
            pygame.draw.rect(ventana, (255, 255, 255), K_RECT, border_radius=12)
            pygame.draw.rect(ventana, (210, 190, 175), K_RECT, 2, border_radius=12)
            draw_button(ventana, K_MENOS, "-", mouse_pos, (210, 150, 90), (230, 175, 115), font_obj=font_large)
            draw_button(ventana, K_MAS, "+", mouse_pos, (210, 150, 90), (230, 175, 115), font_obj=font_large)
            color_k = (150, 90, 200) if (hint_k is not None and (time.time() - hint_t0) < DUR_HINT and k == hint_k) else (30, 25, 20)
            ventana.blit(texto(font_large, f"k = {k}", color_k),
                         texto(font_large, f"k = {k}", color_k).get_rect(center=K_RECT.center))
            if hint_k is not None and (time.time() - hint_t0) < DUR_HINT:
                ventana.blit(texto(font_small, f"Pista: prueba k = {hint_k}", (150, 95, 205)),
                             (K_RECT.x, K_RECT.bottom + 4))

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

        while running:
            tiempo_restante = max(0, Config.LEVEL_TIME - (time.time() - level_start_time))

            if fase == 'resultado' and (time.time() - resultado_t0) >= DUR_RESULTADO:
                if resultado_ok:
                    nuevo_sistema()
                fase = 'esperando'

            if estado_juego == "jugando" and score >= nivel_goal(nivel):
                guardar_reporte()
                progress.registrar_resultado(estudiante, tema_id, nivel, score)
                progress.desbloquear_nivel(estudiante, tema_id, nivel)
                await mostrar_boss(ventana, sound, nivel, nombre_tema(tema_id))
                sound.play('levelup')
                effects.spawn_confetti(pygame.Rect(0, 0, Config.LEFT_WIDTH, 40))
                estado_juego = "modulo_completo" if nivel >= Config.MAX_LEVEL else "nivel_completo"
                overlay_start = time.time()
            elif estado_juego == "jugando" and tiempo_restante <= 0:
                guardar_reporte()
                progress.registrar_resultado(estudiante, tema_id, nivel, score)
                estado_juego = "tiempo_agotado"
                overlay_start = time.time()

            for event in entrada.obtener_eventos():
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
                        await manejar_click_habilidad(golpe_hab)
                    elif fase == 'esperando' and CARD_A.collidepoint(mx, my):
                        fila_activa = 'a'
                    elif fase == 'esperando' and CARD_B.collidepoint(mx, my):
                        fila_activa = 'b'
                    elif fase == 'esperando' and K_MENOS.collidepoint(mx, my):
                        k = max(-6, k - 1)
                        if k == 0:
                            k = -1
                    elif fase == 'esperando' and K_MAS.collidepoint(mx, my):
                        k = min(6, k + 1)
                        if k == 0:
                            k = 1
                    elif fase == 'esperando' and BOTON_APLICAR.collidepoint(mx, my):
                        aplicar_combinacion()
                    elif mx >= Config.LEFT_WIDTH:
                        botones = get_panel_buttons()
                        if botones["estudio"].collidepoint(mx, my):
                            pausar_reloj(await mostrar_zona_estudio(ventana, generar_tablero(), sound, tema_id))
                        elif botones["excel"].collidepoint(mx, my):
                            guardar_reporte(avisar=True)
                        elif botones["menu"].collidepoint(mx, my):
                            guardar_reporte()
                            progress.registrar_resultado(estudiante, tema_id, nivel, score)
                            return 'menu'

                elif event.type == pygame.KEYDOWN and estado_juego == "jugando":
                    if event.key == pygame.K_ESCAPE:
                        pausar_reloj(await mostrar_zona_estudio(ventana, generar_tablero(), sound, tema_id))

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
            ventana.blit(texto(font_large, "Cazaecuaciones", (150, 90, 40)), (40, 60))
            ventana.blit(texto(font_small, "Encuentra el k que hace Fila B + k·Fila A elimine una incógnita.",
                               (110, 80, 50)), (40, 100))
            mouse_pos = entrada.posicion_puntero()
            dibujar_carta(CARD_A, fila_a, "A", fila_activa == 'a')
            dibujar_carta(CARD_B, fila_b, "B", fila_activa == 'b')
            dibujar_preview()
            dibujar_selector_k(mouse_pos)
            draw_button(ventana, BOTON_APLICAR, "Aplicar", mouse_pos, (60, 150, 90), (80, 180, 110),
                       font_obj=font_large)

            rects_hab = rects_habilidades()
            restantes = max(0, Config.MAX_SKILL_USES_PER_LEVEL - habilidades.usos_nivel)
            primer = rects_hab[HABILIDADES_SISTEMAS[0]['id']]
            ventana.blit(texto(font_small, f"Habilidades  ·  usos restantes en el nivel: {restantes}", (92, 52, 36)),
                         (primer.x, primer.y - 22))
            for h in HABILIDADES_SISTEMAS:
                hid = h['id']
                rect = rects_hab[hid]
                estado = habilidades.estado_de(hid)
                if estado == 'limite':
                    base, etiqueta = (150, 140, 135), "Límite"
                elif estado == 'enfriando':
                    base, etiqueta = (128, 128, 140), f"{int(habilidades.segundos_restantes(hid)) + 1}s"
                elif estado == 'lista':
                    base, etiqueta = h['color'], "¡Lista!"
                else:
                    base, etiqueta = tuple(int(c * 0.55) for c in h['color']), "Responder"
                color = h['color'] if rect.collidepoint(mouse_pos) else base
                pygame.draw.rect(ventana, tuple(int(c * 0.5) for c in base), rect.move(0, 3), border_radius=12)
                pygame.draw.rect(ventana, color, rect, border_radius=12)
                pygame.draw.rect(ventana, (255, 226, 90) if estado == 'lista' else (255, 255, 255), rect,
                                 3, border_radius=12)
                icono = _icono_sistema(hid, 30)
                ventana.blit(icono, icono.get_rect(center=(rect.x + 24, rect.centery)))
                ventana.blit(texto(font_small, h['nombre'], (255, 255, 255)), (rect.x + 44, rect.y + 10))
                ventana.blit(texto(font_small, etiqueta, (255, 255, 255)), (rect.x + 44, rect.y + 32))

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
                    nuevo_sistema()
                    fase = 'esperando'
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

                draw_button(ventana, BOTON_REINTENTAR, "Jugar de nuevo", mouse_pos, (60, 150, 90), (80, 180, 110))
                draw_button(ventana, BOTON_MENU, "Menú principal", mouse_pos, (60, 110, 170), (90, 145, 200))

            elif estado_juego == "modulo_completo":
                overlay = pygame.Surface((Config.LEFT_WIDTH, Config.ALTO), pygame.SRCALPHA)
                overlay.fill((10, 10, 10, 175))
                ventana.blit(overlay, (0, 0))
                dibujar_texto_central(f"¡{nombre_tema(tema_id)} completado!",
                                      f"Superaste los {Config.MAX_LEVEL} niveles con {score} puntos",
                                      frase=lore.frase(tema_id, 'nivel'))
                draw_button(ventana, BOTON_MAPA, "Volver al mapa de niveles", mouse_pos,
                           (60, 150, 90), (80, 180, 110))

            pygame.display.flip()
            clock.tick(Config.FPS)
            await asyncio.sleep(0)
