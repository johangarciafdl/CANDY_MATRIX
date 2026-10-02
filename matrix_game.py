# matrix_game.py
"""Minijuego del tema Matrices: match-3 al estilo Candy Crush donde el propio
tablero ES la matriz (cada fruta es a_ij). Vive en su propio módulo para que
cada tema del Hub pueda tener una mecánica de juego distinta (ver vector_game.py)
mientras comparten el mismo marco: panel derecho, cronómetro, habilidades,
Zona de Estudio y exportación a Excel."""
import asyncio
import time
import pygame

from config import Config, font, font_small, font_large, NEGRO, COLOR_MAP
from matrix_logic import generar_tablero, son_adyacentes, matrix_stats
from animations import BoardAnimator
from fruits import get_fruit_sprite, precargar
from learn_zone import mostrar_zona_estudio
from excel_exporter import export_to_excel
from skills import (SistemaHabilidades, HABILIDADES, draw_barra, get_barra_rects,
                    celdas_afectadas, preguntar_para_habilidad, nombre as nombre_habilidad)
from ui import (draw_right_panel, get_panel_buttons, get_fondo_juego, get_area_tablero,
                draw_seleccion, draw_button)
from topics import nombre as nombre_tema
import lore
import effects
import progress
from boss import mostrar_boss

OVERLAY_DURATION = 2.5
CHANGE_HIGHLIGHT_DURATION = 4.0
DUR_FLOTANTE = 0.9
DUR_AVISO = 4.0

BOTON_REINTENTAR = pygame.Rect(Config.LEFT_WIDTH // 2 - 140, Config.ALTO // 2 + 40, 280, 60)
BOTON_MENU = pygame.Rect(Config.LEFT_WIDTH // 2 - 140, Config.ALTO // 2 + 114, 280, 60)
BOTON_MAPA = pygame.Rect(Config.LEFT_WIDTH // 2 - 140, Config.ALTO // 2 + 60, 280, 60)

_PREVIEW = pygame.Surface((Config.TAMANO_CELDA - 6, Config.TAMANO_CELDA - 6), pygame.SRCALPHA)
pygame.draw.rect(_PREVIEW, (255, 255, 255, 110), _PREVIEW.get_rect(), border_radius=10)
pygame.draw.rect(_PREVIEW, (255, 235, 90, 220), _PREVIEW.get_rect(), 3, border_radius=10)

precargar(Config.RADIO_FRUTA)


def nivel_goal(nivel):
    return Config.GOAL_BASE * nivel


def centro_de_celda(i, j):
    x = Config.MARGEN_IZQUIERDO + j * Config.TAMANO_CELDA + Config.TAMANO_CELDA // 2
    y = Config.MARGEN_SUPERIOR + i * Config.TAMANO_CELDA + Config.TAMANO_CELDA // 2
    return int(x), int(y)


def celda_desde_pixel(mx, my):
    if not get_area_tablero().collidepoint(mx, my):
        return None
    col = (mx - Config.MARGEN_IZQUIERDO) // Config.TAMANO_CELDA
    fila = (my - Config.MARGEN_SUPERIOR) // Config.TAMANO_CELDA
    if 0 <= fila < Config.FILAS and 0 <= col < Config.COLUMNAS:
        return (int(fila), int(col))
    return None


async def jugar(ventana, sound, tema_id, estudiante, nivel_inicial=1):
    """Corre partidas de Matrices hasta que el jugador vuelve al menú o cierra
    el juego. Devuelve 'menu' o 'salir'."""
    clock = pygame.time.Clock()
    effects.limpiar()
    primera_vez = True

    while True:
        # ---------- Estado de una partida nueva ----------
        tablero = generar_tablero()
        anim = BoardAnimator(tablero)
        habilidades = SistemaHabilidades()
        habilidad_activa = None
        usos_habilidad = {h['id']: 0 for h in HABILIDADES}

        score = 0
        level = nivel_inicial
        moves_count = 0
        seleccionado = None
        arrastre_origen = None
        running = True
        level_start_time = time.time()
        history = []
        events = []
        flotantes = []
        aviso = None

        estado_juego = "jugando"  # "jugando" | "nivel_completo" | "tiempo_agotado"
        overlay_start = 0.0

        tablero_pre_jugada = None
        changed_cells = set()
        changed_time = 0.0

        if primera_vez:
            frase_entrada = lore.frase(tema_id, 'entrada')
            if frase_entrada:
                aviso = {'texto': frase_entrada, 't0': time.time(), 'color': (60, 110, 170)}
            primera_vez = False

        # ---------- Ayudantes que dependen del estado de esta partida ----------
        def agregar_flotante(texto_flotante, x, y, color=(255, 242, 170)):
            flotantes.append({'texto': texto_flotante, 'x': x, 'y': y,
                              't0': pygame.time.get_ticks() / 1000.0, 'color': color})

        def mostrar_aviso(mensaje, color=(56, 132, 86)):
            nonlocal aviso
            aviso = {'texto': mensaje, 't0': time.time(), 'color': color}

        def pausar_reloj(segundos):
            nonlocal level_start_time
            if segundos:
                level_start_time += segundos
                habilidades.posponer_enfriamientos(segundos)

        def iniciar_jugada(p1, p2):
            """Solo permite intercambiar con una vecina inmediata: una única
            casilla de distancia, nunca más."""
            nonlocal tablero_pre_jugada
            if not son_adyacentes(p1, p2):
                return
            if anim.iniciar_swap(p1, p2):
                tablero_pre_jugada = [fila[:] for fila in tablero]

        def detectar_bonus_filas_columnas(combinaciones):
            bonus = 0
            mensajes = []
            for i in range(Config.FILAS):
                if all((i, j) in combinaciones for j in range(Config.COLUMNAS)):
                    bonus += 50
                    mensajes.append(f"¡Fila {i + 1} completa eliminada! Bonus por operación de fila (+50)")
            for j in range(Config.COLUMNAS):
                if all((i, j) in combinaciones for i in range(Config.FILAS)):
                    bonus += 50
                    mensajes.append(f"¡Columna {j + 1} completa eliminada! Bonus por operación de columna (+50)")
            return bonus, mensajes

        def guardar_reporte(avisar=False):
            resumen = {nombre_habilidad(hid): veces for hid, veces in usos_habilidad.items() if veces}
            ruta, error = export_to_excel(level, score, moves_count, history, events,
                                          matrix_stats(tablero), resumen, nombre_tema(tema_id))
            if ruta:
                events.append(f"Reporte exportado: {ruta}")
                if avisar:
                    import os
                    mostrar_aviso(f"Excel guardado: {os.path.basename(ruta)}", (56, 132, 86))
            elif avisar:
                mostrar_aviso(error or "No se pudo exportar el Excel.", (168, 58, 52))
            return ruta

        async def manejar_click_habilidad(hid):
            nonlocal habilidad_activa
            estado = habilidades.estado_de(hid)

            if estado == 'limite':
                mostrar_aviso(f"Ya gastaste las {Config.MAX_SKILL_USES_PER_LEVEL} habilidades de este nivel.",
                              (168, 58, 52))
            elif estado == 'enfriando':
                mostrar_aviso(f"{nombre_habilidad(hid)} se recarga en {int(habilidades.segundos_restantes(hid)) + 1}s.",
                              (150, 120, 40))
            elif estado == 'lista':
                habilidad_activa = None if habilidad_activa == hid else hid
                if habilidad_activa:
                    mostrar_aviso(f"{nombre_habilidad(hid)} lista: elige la celda del tablero.", (60, 110, 170))
            else:
                acierto, pausa = await preguntar_para_habilidad(ventana, tablero, hid, sound, tema_id)
                pausar_reloj(pausa)
                if acierto:
                    habilidades.otorgar(hid)
                    habilidad_activa = hid
                    mostrar_aviso(f"¡{nombre_habilidad(hid)} cargada! Elige la celda del tablero.", (56, 132, 86))
                else:
                    mostrar_aviso("Respuesta incorrecta: la habilidad no se cargó.", (168, 58, 52))

        def usar_habilidad_en(celda):
            nonlocal habilidad_activa, tablero_pre_jugada
            hid = habilidad_activa
            celdas = celdas_afectadas(hid, tablero, *celda)
            previo = [fila[:] for fila in tablero]
            if anim.iniciar_habilidad(celdas, nombre_habilidad(hid)):
                tablero_pre_jugada = previo
                habilidades.consumir(hid)
                usos_habilidad[hid] += 1
                events.append(f"Habilidad {nombre_habilidad(hid)} usada en la celda "
                              f"({celda[0] + 1},{celda[1] + 1}): {len(celdas)} frutas eliminadas")
                habilidad_activa = None

        def procesar_eventos_animacion():
            nonlocal score, moves_count, changed_cells, changed_time, tablero_pre_jugada

            for ev in anim.update():
                tipo = ev['tipo']

                if tipo == 'movimiento_valido':
                    moves_count += 1

                elif tipo == 'movimiento_invalido':
                    sound.play('error')
                    (i, j), _ = ev['par']
                    x, y = centro_de_celda(i, j)
                    agregar_flotante("Sin combinación", x, y - 10, (255, 220, 220))

                elif tipo == 'eliminadas':
                    celdas, cascada = ev['celdas'], ev['cascada']
                    bonus, mensajes = detectar_bonus_filas_columnas(celdas)
                    puntos = len(celdas) * 10 * cascada + bonus
                    score += puntos
                    sound.play('explosion')

                    etiqueta_hab = ev.get('habilidad')
                    if etiqueta_hab:
                        descripcion = f"{etiqueta_hab}: eliminó {len(celdas)} frutas (+{puntos} pts)"
                    else:
                        descripcion = f"Se eliminaron {len(celdas)} frutas (cascada x{cascada}, +{puntos} pts)"
                    if mensajes:
                        descripcion += " | " + " | ".join(mensajes)

                    events.append(descripcion)
                    history.append({'matriz': [fila[:] for fila in tablero], 'evento': descripcion})

                    fila_media = sum(i for i, _ in celdas) / len(celdas)
                    col_media = sum(j for _, j in celdas) / len(celdas)
                    x, y = centro_de_celda(fila_media, col_media)
                    primer_i, primer_j = next(iter(celdas))
                    valor = tablero[primer_i][primer_j]
                    if isinstance(valor, int) and 0 <= valor < len(COLOR_MAP):
                        effects.spawn_burst(x, y, COLOR_MAP[valor], cantidad=8 + 3 * cascada)
                    if etiqueta_hab:
                        texto_flotante = f"{etiqueta_hab}  +{puntos}"
                    elif cascada == 1:
                        texto_flotante = f"+{puntos}"
                    else:
                        texto_flotante = f"¡Combo x{cascada}!  +{puntos}"
                    agregar_flotante(texto_flotante, x, y)

                elif tipo == 'estable' and tablero_pre_jugada is not None:
                    changed_cells = {
                        (i, j)
                        for i in range(Config.FILAS)
                        for j in range(Config.COLUMNAS)
                        if tablero[i][j] != tablero_pre_jugada[i][j]
                    }
                    changed_time = time.time()
                    tablero_pre_jugada = None

        def dibujar_tablero():
            ventana.set_clip(get_area_tablero())
            for i in range(Config.FILAS):
                for j in range(Config.COLUMNAS):
                    valor = tablero[i][j]
                    if valor is None:
                        continue
                    escala = anim.escala(i, j)
                    if escala < 0.05:
                        continue

                    ox, oy = anim.offset(i, j)
                    x, y = centro_de_celda(i, j)
                    cx, cy = int(x + ox), int(y + oy)

                    if seleccionado == (i, j) and not anim.ocupado():
                        draw_seleccion(ventana, (cx, cy), Config.RADIO_FRUTA)

                    sprite = get_fruit_sprite(valor, Config.RADIO_FRUTA)
                    if escala != 1.0:
                        ancho = max(1, int(sprite.get_width() * escala))
                        alto = max(1, int(sprite.get_height() * escala))
                        sprite = pygame.transform.smoothscale(sprite, (ancho, alto))
                    ventana.blit(sprite, sprite.get_rect(center=(cx, cy)))
            ventana.set_clip(None)

        def dibujar_previsualizacion():
            if not habilidad_activa or anim.ocupado():
                return
            celda = celda_desde_pixel(*pygame.mouse.get_pos())
            if not celda:
                return
            for (a, b) in celdas_afectadas(habilidad_activa, tablero, *celda):
                x, y = centro_de_celda(a, b)
                ventana.blit(_PREVIEW, _PREVIEW.get_rect(center=(x, y)))

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

        def dibujar_texto_central(texto_central, sub=None, frase=None):
            render = font_large.render(texto_central, True, NEGRO)
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

            if estado_juego == "jugando" and score >= nivel_goal(level):
                guardar_reporte()
                progress.registrar_resultado(estudiante, tema_id, level, score)
                progress.desbloquear_nivel(estudiante, tema_id, level)
                await mostrar_boss(ventana, sound, level, nombre_tema(tema_id))
                sound.play('levelup')
                effects.spawn_confetti(pygame.Rect(0, 0, Config.LEFT_WIDTH, 40))
                estado_juego = "modulo_completo" if level >= Config.MAX_LEVEL else "nivel_completo"
                overlay_start = time.time()
            elif estado_juego == "jugando" and tiempo_restante <= 0:
                guardar_reporte()
                progress.registrar_resultado(estudiante, tema_id, level, score)
                estado_juego = "tiempo_agotado"
                overlay_start = time.time()

            procesar_eventos_animacion()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if estado_juego == "jugando":
                        guardar_reporte()
                        progress.registrar_resultado(estudiante, tema_id, level, score)
                    return 'salir'

                elif event.type == pygame.MOUSEBUTTONDOWN and estado_juego == "jugando":
                    mx, my = event.pos

                    if event.button == 3:
                        habilidad_activa = None
                        continue

                    rects_hab = get_barra_rects()
                    golpe_hab = next((hid for hid, r in rects_hab.items() if r.collidepoint(mx, my)), None)

                    if golpe_hab:
                        await manejar_click_habilidad(golpe_hab)

                    elif mx < Config.LEFT_WIDTH:
                        celda = celda_desde_pixel(mx, my)
                        if celda and not anim.ocupado():
                            if habilidad_activa:
                                usar_habilidad_en(celda)
                            else:
                                arrastre_origen = celda
                                if seleccionado is None or seleccionado == celda:
                                    seleccionado = None if seleccionado == celda else celda
                                elif son_adyacentes(seleccionado, celda):
                                    iniciar_jugada(seleccionado, celda)
                                    seleccionado = None
                                    arrastre_origen = None
                                else:
                                    seleccionado = celda
                    else:
                        botones = get_panel_buttons()
                        if botones["estudio"].collidepoint(mx, my):
                            pausar_reloj(await mostrar_zona_estudio(ventana, tablero, sound, tema_id))
                        elif botones["excel"].collidepoint(mx, my):
                            guardar_reporte(avisar=True)
                        elif botones["menu"].collidepoint(mx, my):
                            guardar_reporte()
                            progress.registrar_resultado(estudiante, tema_id, level, score)
                            return 'menu'

                elif event.type == pygame.MOUSEBUTTONUP and estado_juego == "jugando":
                    if arrastre_origen and not anim.ocupado() and not habilidad_activa:
                        celda = celda_desde_pixel(*event.pos)
                        if celda and celda != arrastre_origen and son_adyacentes(arrastre_origen, celda):
                            iniciar_jugada(arrastre_origen, celda)
                            seleccionado = None
                    arrastre_origen = None

                elif event.type == pygame.KEYDOWN and estado_juego == "jugando":
                    if event.key == pygame.K_ESCAPE:
                        if habilidad_activa:
                            habilidad_activa = None
                        else:
                            pausar_reloj(await mostrar_zona_estudio(ventana, tablero, sound, tema_id))

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
            ventana.blit(get_fondo_juego(), (0, 0))
            dibujar_tablero()
            dibujar_previsualizacion()
            dibujar_flotantes()
            effects.update_and_draw(ventana, 1.0 / Config.FPS)
            draw_barra(ventana, habilidades, habilidad_activa, pygame.mouse.get_pos())
            dibujar_aviso()

            resaltado = changed_cells if (time.time() - changed_time) < CHANGE_HIGHLIGHT_DURATION else set()
            draw_right_panel(ventana, level, score, moves_count, tiempo_restante,
                             goal=nivel_goal(level), tablero=tablero, changed_cells=resaltado,
                             tema_nombre=nombre_tema(tema_id))

            if estado_juego == "nivel_completo":
                overlay = pygame.Surface((Config.LEFT_WIDTH, Config.ALTO), pygame.SRCALPHA)
                overlay.fill((10, 10, 10, 160))
                ventana.blit(overlay, (0, 0))
                dibujar_texto_central("¡Nivel superado!", f"Nivel {level} completado con {score} puntos",
                                      frase=lore.frase(tema_id, 'nivel'))

                if time.time() - overlay_start >= OVERLAY_DURATION:
                    tablero = generar_tablero()
                    anim.reiniciar(tablero)
                    habilidades.reiniciar_nivel()
                    habilidad_activa = None
                    score = 0
                    moves_count = 0
                    level += 1
                    level_start_time = time.time()
                    estado_juego = "jugando"
                    seleccionado = None
                    arrastre_origen = None
                    tablero_pre_jugada = None
                    changed_cells = set()
                    changed_time = 0.0
                    flotantes.clear()

            elif estado_juego == "tiempo_agotado":
                overlay = pygame.Surface((Config.LEFT_WIDTH, Config.ALTO), pygame.SRCALPHA)
                overlay.fill((10, 10, 10, 170))
                ventana.blit(overlay, (0, 0))
                dibujar_texto_central("¡Se acabó el tiempo!",
                                      f"Nivel {level} — {score}/{nivel_goal(level)} puntos",
                                      frase=lore.frase(tema_id, 'tiempo_agotado'))

                mouse_pos = pygame.mouse.get_pos()
                draw_button(ventana, BOTON_REINTENTAR, "Jugar de nuevo", mouse_pos,
                           (60, 150, 90), (80, 180, 110))
                draw_button(ventana, BOTON_MENU, "Menú principal", mouse_pos,
                           (60, 110, 170), (90, 145, 200))

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
            await asyncio.sleep(0)
