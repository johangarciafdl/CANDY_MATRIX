# learn_zone.py
import asyncio
import pygame, sys, time
from config import Config, font, font_small, font_large
from ui import draw_button
from quiz_system import pick_question
from topics import nombre as nombre_tema

MATRICES_PAGES = [
    ("¿Qué es una matriz?", [
        "Una matriz es una tabla de números organizada en filas y columnas.",
        "Se escribe A = [aij], donde 'i' es la fila y 'j' es la columna del dato.",
        "El propio tablero de Candy Matrix ES una matriz: cada caramelo es un número.",
        "El tamaño de una matriz se llama 'dimensión': 8x8 significa 8 filas y 8 columnas.",
    ]),
    ("Suma y resta de matrices", [
        "Para sumar A+B, se suman los elementos que están en la misma posición (fila, columna).",
        "Ejemplo: [1 2] + [5 1] = [6 3]   (fila 1);  [3 4] + [0 2] = [3 6]  (fila 2).",
        "Solo se pueden sumar matrices que tengan exactamente la misma dimensión.",
        "La resta funciona igual, pero restando celda por celda en vez de sumar.",
    ]),
    ("Determinante y matrices invertibles", [
        "El determinante de una matriz 2x2 [[a,b],[c,d]] se calcula como a*d - b*c.",
        "Si det(A) = 0, la matriz se llama 'singular' y NO tiene inversa.",
        "Si det(A) != 0, existe una matriz inversa A^-1 tal que A * A^-1 = Identidad.",
        "Intuición: el determinante mide cuánto 'estira o encoge' el área una transformación.",
    ]),
    ("Rango, autovalores y autovectores", [
        "El rango es el número de filas (o columnas) linealmente independientes de la matriz.",
        "Un autovector v de A cumple: A*v = λ*v, es decir, solo cambia de escala (λ) sin girar.",
        "La traza tr(A) (suma de la diagonal) es igual a la suma de todos los autovalores.",
        "Estos conceptos se usan en Google PageRank, compresión de imágenes y gráficos 3D.",
    ]),
    ("Conecta la teoría con el tablero", [
        "Cada fila y columna del tablero tiene una suma: es como sumar un vector fila o columna.",
        "Cuando eliminas 3 o más caramelos iguales, en el fondo estás reduciendo esa fila/columna.",
        "Observa la gráfica de barras: representa el vector de sumas por fila del tablero actual.",
        "Pulsa 'Practicar' para responder preguntas usando los números reales de tu partida.",
    ]),
    ("Consejos de estudio", [
        "Practica con ejercicios cortos y frecuentes en vez de sesiones muy largas.",
        "Haz tarjetas (flashcards) con las definiciones clave: rango, determinante, autovalor.",
        "Divide tu tiempo: 20 min de teoría + 20 min de práctica con el modo Quiz.",
        "Equivócate sin miedo: cada respuesta incorrecta trae una explicación para aprender.",
    ]),
]

VECTORES_PAGES = [
    ("¿Qué es un vector?", [
        "Un vector es una lista ordenada de números: v = (v1, v2, ..., vn).",
        "Cada fila (o columna) del tablero de Candy Matrix es, en sí misma, un vector.",
        "La 'dimensión' de un vector es su cantidad de componentes: una fila de 8 celdas es un vector de R^8.",
        "Los vectores representan magnitudes con varias componentes: posición, velocidad, fuerza, etc.",
    ]),
    ("Suma y resta de vectores", [
        "Para sumar u+v se suman componente a componente: (u1+v1, u2+v2, ..., un+vn).",
        "Geométricamente, sumar vectores es colocarlos 'punta con cola' (regla del paralelogramo).",
        "Solo se pueden sumar vectores de la misma dimensión, igual que con las matrices.",
        "Restar vectores es sumar el opuesto: u - v = u + (-v).",
    ]),
    ("Producto escalar (producto punto)", [
        "El producto punto u·v = u1*v1 + u2*v2 + ... + un*vn, y el resultado es un número (escalar).",
        "Ejemplo: u=(1,2), v=(3,4)  ->  u·v = 1*3 + 2*4 = 11.",
        "Si u·v = 0, los vectores son ortogonales (perpendiculares entre sí).",
        "El producto punto mide cuánto 'apuntan en la misma dirección' dos vectores.",
    ]),
    ("Norma (magnitud) y vectores unitarios", [
        "La norma ||v|| es la 'longitud' del vector: ||v|| = raíz(v1^2 + v2^2 + ... + vn^2).",
        "Ejemplo: v=(3,4)  ->  ||v|| = raíz(9+16) = raíz(25) = 5.",
        "Un vector unitario tiene norma 1; para normalizar v se calcula v / ||v||.",
        "||v||^2 (norma al cuadrado) es v·v, el producto punto de un vector consigo mismo.",
    ]),
    ("Conecta la teoría con el tablero", [
        "Cada fila del tablero es un vector: la fila i es v_i = (a_i1, a_i2, ..., a_i8).",
        "Al eliminar 3+ caramelos iguales en una fila, estás modificando ese vector componente a componente.",
        "El diagrama muestra dos filas del tablero como vectores 2D (sus dos primeras componentes) y su suma.",
        "Pulsa 'Practicar' para calcular sumas, productos punto y normas con los números reales de tu partida.",
    ]),
    ("Consejos de estudio", [
        "Practica calculando productos punto a mano antes de usar calculadora: refuerza el patrón.",
        "Dibuja los vectores en papel cuadriculado para visualizar la suma y la ortogonalidad.",
        "Relaciona cada concepto con un ejemplo físico: velocidad, fuerza, desplazamiento.",
        "Equivócate sin miedo: cada respuesta incorrecta trae una explicación para aprender.",
    ]),
]

SISTEMAS_PAGES = [
    ("¿Qué es un sistema de ecuaciones lineales?", [
        "Es un conjunto de ecuaciones lineales que comparten las mismas incógnitas (x, y, ...).",
        "Resolverlo es encontrar los valores de esas incógnitas que cumplen TODAS las ecuaciones a la vez.",
        "Se puede escribir como Ax = b: A son los coeficientes, x las incógnitas, b los términos independientes.",
        "Geométricamente, cada ecuación 2D es una recta; la solución es donde esas rectas se cruzan.",
    ]),
    ("Tipos de solución", [
        "Solución única: las rectas se cruzan en un solo punto (el caso más común).",
        "Infinitas soluciones: las ecuaciones describen la misma recta (son múltiplos entre sí).",
        "Sin solución: las rectas son paralelas y nunca se tocan (sistema 'inconsistente').",
        "Al escalonar, 0=0 señala infinitas soluciones; 0=c (c≠0) señala que no hay solución.",
    ]),
    ("Operaciones elementales de fila", [
        "1) Sumar un múltiplo de una ecuación a otra: no cambia el conjunto solución.",
        "2) Intercambiar el orden de dos ecuaciones: tampoco lo cambia.",
        "3) Multiplicar una ecuación por un escalar DISTINTO de cero: tampoco lo cambia.",
        "Estas tres operaciones son la base de la eliminación gaussiana.",
    ]),
    ("Eliminación gaussiana paso a paso", [
        "Objetivo: combinar ecuaciones hasta que una quede con una sola incógnita.",
        "Ejemplo: 2x+3y=11  y  4x-y=1. Combinando Fila2 + (-2)·Fila1: 0x -7y = -21, y=3.",
        "Con y=3 se sustituye hacia atrás en la primera ecuación para hallar x.",
        "Cada combinación válida elimina una incógnita: así se reduce el sistema paso a paso.",
    ]),
    ("Conecta la teoría con el juego", [
        "En Cazaecuaciones, cada ecuación es una carta con coeficientes; tú eliges el multiplicador k.",
        "Buscas el k que hace Fila B + k·Fila A = una fila con un coeficiente en cero.",
        "Ese es exactamente el paso central de la eliminación gaussiana, ¡pero jugable!",
        "Pulsa 'Practicar' para resolver sistemas 2x2 con los números de tus propias ecuaciones.",
    ]),
    ("Consejos de estudio", [
        "Antes de combinar, mira si algún coeficiente de una fila es múltiplo del de la otra: ahí está el k.",
        "Verifica siempre tu solución sustituyéndola de vuelta en las ecuaciones originales.",
        "Practica primero con sistemas 2x2 antes de pasar a sistemas más grandes.",
        "Equivócate sin miedo: cada respuesta incorrecta trae una explicación para aprender.",
    ]),
]

LEARN_PAGES = {
    'matrices': MATRICES_PAGES,
    'vectores': VECTORES_PAGES,
    'sistemas': SISTEMAS_PAGES,
}


def draw_row_sums_bar(surface, area_rect, tablero):
    row_sums = [sum(v for v in row if isinstance(v, int) and v >= 0) for row in tablero]
    if not row_sums:
        return
    maxv = max(row_sums) or 1
    padding = 8
    gw = area_rect.width - 2 * padding
    gh = area_rect.height - 2 * padding
    bar_w = gw / len(row_sums) - 6
    for i, val in enumerate(row_sums):
        x = area_rect.x + padding + i * (bar_w + 6)
        h = int((val / maxv) * (gh - 20))
        y = area_rect.y + area_rect.height - padding - h
        pygame.draw.rect(surface, (100, 180, 220), (x, y, int(bar_w), h), border_radius=3)
        lbl = font_small.render(str(val), True, (20, 20, 20))
        surface.blit(lbl, (x, y - 18))
    surface.blit(font_small.render('Vector de sumas por fila (tablero actual)', True, (10, 10, 10)),
                 (area_rect.x + padding, area_rect.y - 4))


def draw_transform_demo(surface, area_rect, tablero=None):
    M = [[1.2, 0.6], [-0.5, 1.0]]
    cx = area_rect.x + area_rect.width // 2
    cy = area_rect.y + area_rect.height // 2
    scale = min(area_rect.width, area_rect.height) * 0.18
    pts = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
    pygame.draw.line(surface, (180, 180, 180), (cx - scale * 2, cy), (cx + scale * 2, cy), 1)
    pygame.draw.line(surface, (180, 180, 180), (cx, cy - scale * 2), (cx, cy + scale * 2), 1)
    transformed = []
    for (x, y) in pts:
        tx = M[0][0] * x + M[0][1] * y
        ty = M[1][0] * x + M[1][1] * y
        transformed.append((int(cx + tx * scale), int(cy - ty * scale)))
    pygame.draw.lines(surface, (220, 100, 80), False, transformed, 3)
    orig = [(int(cx + x * scale), int(cy - y * scale)) for (x, y) in pts]
    pygame.draw.lines(surface, (120, 120, 120), False, orig, 1)
    surface.blit(font_small.render('Cuadrado original (gris) vs transformado por A (rojo)', True, (10, 10, 10)),
                 (area_rect.x, area_rect.y - 20))


def draw_determinant_demo(surface, area_rect, tablero=None):
    m2x2 = [[3, 1], [2, 4]]
    det = m2x2[0][0] * m2x2[1][1] - m2x2[0][1] * m2x2[1][0]
    surface.blit(font.render('Ejemplo:  A = [ 3  1 ]', True, (20, 20, 20)), (area_rect.x, area_rect.y))
    surface.blit(font.render('               [ 2  4 ]', True, (20, 20, 20)), (area_rect.x, area_rect.y + 26))
    surface.blit(font.render(f'det(A) = 3*4 - 1*2 = {det}', True, (150, 20, 20)), (area_rect.x, area_rect.y + 60))
    surface.blit(font_small.render('Como det(A) != 0, la matriz A es invertible.', True, (40, 40, 40)),
                 (area_rect.x, area_rect.y + 92))


def draw_dot_product_demo(surface, area_rect, tablero=None):
    u, v = (1, 2), (3, 4)
    dot = u[0] * v[0] + u[1] * v[1]
    surface.blit(font.render(f'Ejemplo:  u = {u},  v = {v}', True, (20, 20, 20)), (area_rect.x, area_rect.y))
    surface.blit(font.render(f'u·v = {u[0]}*{v[0]} + {u[1]}*{v[1]} = {dot}', True, (150, 20, 20)),
                 (area_rect.x, area_rect.y + 34))
    surface.blit(font_small.render('Como u·v != 0, u y v NO son ortogonales.', True, (40, 40, 40)),
                 (area_rect.x, area_rect.y + 68))


def draw_norm_demo(surface, area_rect, tablero=None):
    v = (3, 4)
    norma2 = v[0] ** 2 + v[1] ** 2
    surface.blit(font.render(f'Ejemplo:  v = {v}', True, (20, 20, 20)), (area_rect.x, area_rect.y))
    surface.blit(font.render(f'||v||^2 = {v[0]}^2 + {v[1]}^2 = {norma2}', True, (150, 20, 20)),
                 (area_rect.x, area_rect.y + 34))
    surface.blit(font.render(f'||v|| = raíz({norma2}) = {int(norma2 ** 0.5)}', True, (150, 20, 20)),
                 (area_rect.x, area_rect.y + 64))


def draw_vector_demo(surface, area_rect, tablero=None):
    """Dibuja dos filas del tablero (sus dos primeras componentes) como vectores 2D y su suma."""
    if tablero and len(tablero) >= 2:
        fila_u = [v for v in tablero[0] if isinstance(v, int) and v >= 0][:2]
        fila_v = [v for v in tablero[1] if isinstance(v, int) and v >= 0][:2]
    else:
        fila_u, fila_v = [], []
    u = (fila_u + [0, 0])[:2]
    v = (fila_v + [0, 0])[:2]
    suma = (u[0] + v[0], u[1] + v[1])

    ox = area_rect.x + area_rect.width // 3
    oy = area_rect.y + area_rect.height - 20
    escala = min(area_rect.width / 3, area_rect.height) / max(1, max(abs(x) for x in (*u, *v, *suma)) or 1)

    def punto(vec):
        return (int(ox + vec[0] * escala), int(oy - vec[1] * escala))

    pygame.draw.line(surface, (180, 180, 180), (area_rect.x, oy), (area_rect.x + area_rect.width, oy), 1)
    pygame.draw.line(surface, (180, 180, 180), (ox, area_rect.y), (ox, area_rect.y + area_rect.height), 1)

    def flecha(vec, color, etiqueta):
        fin = punto(vec)
        pygame.draw.line(surface, color, (ox, oy), fin, 3)
        pygame.draw.circle(surface, color, fin, 4)
        surface.blit(font_small.render(etiqueta, True, color), (fin[0] + 6, fin[1] - 10))

    flecha(u, (60, 140, 200), f'u={tuple(u)}')
    flecha(v, (220, 100, 80), f'v={tuple(v)}')
    flecha(suma, (90, 160, 90), f'u+v={suma}')
    surface.blit(font_small.render('u = fila 1, v = fila 2 (2 primeras componentes)', True, (10, 10, 10)),
                 (area_rect.x, area_rect.y - 4))


def draw_elimination_demo(surface, area_rect, tablero=None):
    surface.blit(font.render('2x + 3y = 11', True, (20, 20, 20)), (area_rect.x, area_rect.y))
    surface.blit(font.render('4x -  y =  1', True, (20, 20, 20)), (area_rect.x, area_rect.y + 28))
    surface.blit(font_small.render('Fila2 + (-2)·Fila1  ->  elimina x:', True, (90, 60, 30)),
                 (area_rect.x, area_rect.y + 62))
    surface.blit(font.render('0x - 7y = -21   ->   y = 3', True, (150, 20, 20)), (area_rect.x, area_rect.y + 88))
    surface.blit(font_small.render('Sustituyendo y=3 en la fila 1: x = 1', True, (40, 40, 40)),
                 (area_rect.x, area_rect.y + 122))


PAGE_VISUALS = {
    ('matrices', "Determinante y matrices invertibles"): draw_determinant_demo,
    ('matrices', "Rango, autovalores y autovectores"): draw_transform_demo,
    ('matrices', "Conecta la teoría con el tablero"): draw_row_sums_bar,
    ('vectores', "Producto escalar (producto punto)"): draw_dot_product_demo,
    ('vectores', "Norma (magnitud) y vectores unitarios"): draw_norm_demo,
    ('vectores', "Conecta la teoría con el tablero"): draw_vector_demo,
    ('sistemas', "Eliminación gaussiana paso a paso"): draw_elimination_demo,
}


async def mostrar_zona_estudio(ventana, tablero=None, sound=None, tema_id='matrices'):
    """Modal de estudio con dos pestañas: Teoría (slideshow) y Practicar (quiz interactivo)."""
    paginas = LEARN_PAGES.get(tema_id, LEARN_PAGES['matrices'])
    page = 0
    modo = 'teoria'  # 'teoria' | 'quiz'
    quiz_state = 'pregunta'  # 'pregunta' | 'feedback'
    current_q = None
    selected_idx = None
    aciertos, total = 0, 0
    clock = pygame.time.Clock()
    tiempo_entrada = time.time()

    w, h = 940, 560
    rx = (Config.ANCHO - w) // 2
    ry = (Config.ALTO - h) // 2
    rect = pygame.Rect(rx, ry, w, h)

    tab_teoria = pygame.Rect(rect.x + 24, rect.y + 16, 160, 42)
    tab_quiz = pygame.Rect(rect.x + 194, rect.y + 16, 160, 42)
    btn_cerrar = pygame.Rect(rect.right - 130, rect.y + 16, 106, 42)
    btn_prev = pygame.Rect(rect.x + 24, rect.bottom - 60, 130, 42)
    btn_next = pygame.Rect(rect.right - 154, rect.bottom - 60, 130, 42)

    def nueva_pregunta():
        nonlocal current_q, quiz_state, selected_idx
        tab = tablero if tablero is not None else [[i + j for j in range(Config.COLUMNAS)] for i in range(Config.FILAS)]
        current_q = pick_question(tab, tema_id)
        quiz_state = 'pregunta'
        selected_idx = None

    while True:
        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return time.time() - tiempo_entrada
                if modo == 'teoria':
                    if ev.key == pygame.K_RIGHT:
                        page = min(page + 1, len(paginas) - 1)
                    if ev.key == pygame.K_LEFT:
                        page = max(page - 1, 0)
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if btn_cerrar.collidepoint(mx, my):
                    return time.time() - tiempo_entrada
                if tab_teoria.collidepoint(mx, my):
                    modo = 'teoria'
                elif tab_quiz.collidepoint(mx, my):
                    modo = 'quiz'
                    if current_q is None:
                        nueva_pregunta()
                elif modo == 'teoria':
                    if btn_prev.collidepoint(mx, my):
                        page = max(page - 1, 0)
                    elif btn_next.collidepoint(mx, my):
                        page = min(page + 1, len(paginas) - 1)
                elif modo == 'quiz' and current_q is not None:
                    if quiz_state == 'pregunta':
                        for idx, opt_rect in enumerate(quiz_option_rects):
                            if opt_rect.collidepoint(mx, my):
                                selected_idx = idx
                                total += 1
                                if idx == current_q['correct_idx']:
                                    aciertos += 1
                                    if sound:
                                        sound.play('correct')
                                elif sound:
                                    sound.play('error')
                                quiz_state = 'feedback'
                    else:
                        if btn_next_q.collidepoint(mx, my):
                            nueva_pregunta()

        # ---------- Fondo oscurecido ----------
        s = pygame.Surface((Config.ANCHO, Config.ALTO), pygame.SRCALPHA)
        s.fill((10, 10, 10, 190))
        ventana.blit(s, (0, 0))

        pygame.draw.rect(ventana, (247, 247, 253), rect, border_radius=16)
        pygame.draw.rect(ventana, (200, 200, 200), rect, 2, border_radius=16)

        ventana.blit(font_small.render(f'Tema: {nombre_tema(tema_id)}', True, (120, 90, 60)), (rect.x + 24, rect.y - 22))

        # ---------- Pestañas ----------
        draw_button(ventana, tab_teoria, "Teoría", mouse_pos,
                    (180, 90, 60) if modo == 'teoria' else (150, 150, 150),
                    (210, 120, 85))
        draw_button(ventana, tab_quiz, "Practicar", mouse_pos,
                    (60, 120, 200) if modo == 'quiz' else (150, 150, 150),
                    (90, 150, 230))
        draw_button(ventana, btn_cerrar, "Cerrar", mouse_pos, (150, 60, 60), (190, 80, 80), font_obj=font_small)

        quiz_option_rects = []
        btn_next_q = None

        if modo == 'teoria':
            title, lines = paginas[page]
            ventana.blit(font_large.render(title, True, (20, 20, 20)), (rect.x + 24, rect.y + 78))
            y_offset = rect.y + 122
            for l in lines:
                ventana.blit(font.render('• ' + l, True, (40, 40, 40)), (rect.x + 24, y_offset))
                y_offset += 28

            viz_area = pygame.Rect(rect.x + 30, y_offset + 24, rect.width - 60, 150)
            visual_fn = PAGE_VISUALS.get((tema_id, title))
            if visual_fn:
                visual_fn(ventana, viz_area, tablero)

            # Paginación (puntos) + botones
            for i in range(len(paginas)):
                cx = rect.centerx - (len(paginas) * 14) // 2 + i * 14
                color = (180, 90, 60) if i == page else (210, 200, 195)
                pygame.draw.circle(ventana, color, (cx, rect.bottom - 78), 5)

            draw_button(ventana, btn_prev, "← Anterior", mouse_pos, (190, 170, 160), (210, 190, 180), font_obj=font_small)
            draw_button(ventana, btn_next, "Siguiente →", mouse_pos, (190, 170, 160), (210, 190, 180), font_obj=font_small)

        else:  # modo == 'quiz'
            if current_q is None:
                nueva_pregunta()

            marcador = font_small.render(f"Aciertos: {aciertos}/{total}", True, (60, 60, 60))
            ventana.blit(marcador, (rect.right - 170, rect.y + 68))

            y = rect.y + 100
            for l in current_q['lines']:
                ventana.blit(font_large.render(l, True, (20, 20, 20)), (rect.x + 24, y))
                y += 34

            y += 16
            for idx, opt in enumerate(current_q['options']):
                opt_rect = pygame.Rect(rect.x + 40, y, rect.width - 80, 50)
                quiz_option_rects.append(opt_rect)

                base_color = (230, 225, 240)
                hover_color = (215, 210, 235)
                if quiz_state == 'feedback':
                    if idx == current_q['correct_idx']:
                        base_color = hover_color = (170, 220, 170)
                    elif idx == selected_idx:
                        base_color = hover_color = (230, 160, 160)
                draw_button(ventana, opt_rect, opt, mouse_pos, base_color, hover_color, text_color=(20, 20, 20))
                y += 62

            if quiz_state == 'feedback':
                es_correcto = selected_idx == current_q['correct_idx']
                msg = "¡Correcto!" if es_correcto else "No es correcto."
                color_msg = (30, 130, 40) if es_correcto else (170, 40, 40)
                ventana.blit(font_large.render(msg, True, color_msg), (rect.x + 24, y + 6))

                exp_lines = _wrap(current_q.get('explanation', ''), 78)
                yy = y + 46
                for l in exp_lines:
                    ventana.blit(font_small.render(l, True, (50, 50, 50)), (rect.x + 24, yy))
                    yy += 22

                btn_next_q = pygame.Rect(rect.right - 190, rect.bottom - 60, 150, 42)
                draw_button(ventana, btn_next_q, "Siguiente", mouse_pos, (60, 150, 90), (80, 180, 110))

        pygame.display.flip()
        clock.tick(30)
        await asyncio.sleep(0)


def _wrap(text, max_len=78):
    if not text:
        return []
    words = text.split()
    lines = []
    cur = words[0] if words else ''
    for w in words[1:]:
        if len(cur + ' ' + w) <= max_len:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
