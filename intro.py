# intro.py
"""Prólogo cinemático de apertura (GDD sección 5.1: "Prólogo cinematográfico").

Cuenta el origen de Matrixia en seis escenas, sin imágenes ni video: todo se
dibuja con primitivas de pygame.

    1. Fragmentos   números sueltos flotan en la oscuridad
    2. Convergencia se ordenan y forman la Matriz Original
    3. La Matriz    completa, entre corchetes, con una onda de luz
    4. El Vacío     el antagonista del juego aparece y la agrieta
    5. Ruptura      la matriz estalla en fragmentos
    6. La Chispa    en la oscuridad se enciende el Aprendiz (el jugador)
    7. Título       CANDY MATRIX, letra por letra

La escena 4 enlaza la cinemática con el jefe del juego (boss.py): en el lore,
El Vacío es "una entidad negra de matrices fracturadas con símbolo 0", y antes
la matriz se rompía sin causa. La escena 6 es "la luz" que aparecía después:
era un punto suelto en una pantalla vacía, y ahora es el Aprendiz que atrae de
vuelta los fragmentos, que es lo que la narración dice que ocurre.

Rendimiento: esto corre en el navegador (WebAssembly), donde crear superficies
en cada fotograma se nota. Todo lo costoso (fondo, resplandores, fichas, letras)
se dibuja una vez y se guarda; la luz se suma con BLEND_ADD, que es como se
consigue el aspecto de resplandor sin calcular nada por píxel.

Se puede saltar con un clic, un toque o una tecla; siempre termina con un
fundido a negro, para que la pantalla siguiente (clara) no aparezca de golpe.
"""
import asyncio
import math
import random
import time
from collections import OrderedDict

import pygame
import pygame.gfxdraw

import entrada
from config import Config, COLOR_MAP
from fuentes import fuente, TITULO, TEXTO_FUERTE

ANCHO, ALTO = Config.ANCHO, Config.ALTO
CX, CY = ANCHO // 2, ALTO // 2 - 10

# -------------------- Línea de tiempo (segundos) --------------------
T_APERTURA = 1.0       # fundido desde negro, entran las franjas de cine
T_FRAGMENTOS = 3.4     # fin de la escena 1
T_CONVERGENCIA = 5.2   # fin de la escena 2
T_MATRIZ = 7.8         # fin de la escena 3
T_VACIO = 9.8          # fin de la escena 4
T_RUPTURA = 11.4       # fin de la escena 5 (deja un respiro breve en negro)
T_CHISPA = 14.8        # fin de la escena 6
TOTAL = 19.5           # fin del título; después continúa sola
DURACION_SALIDA = 0.6  # fundido a negro final (también al saltar)

# Margen antes de permitir que un clic salte la cinemática. En el navegador el
# juego no arranca hasta que el usuario toca la pantalla (lo exige el navegador
# para poder reproducir audio), y ese mismo toque llega al canvas como un clic:
# sin este margen la cinemática se saltaba sola en el celular.
ESPERA_ANTES_DE_SALTAR = 0.8

GRID = 6
CELDA = 52
FRANJA = 64  # alto de las franjas negras de cine

NARRACION = [
    # (desde, hasta, texto)
    (5.4, 7.7, "Antes de que existieran los mundos, existía una sola matriz."),
    (7.9, 9.7, "Hasta que El Vacío quiso reducirla a cero."),
    (9.95, 11.35, "El conocimiento no desapareció. Se fragmentó."),
    (11.9, 14.6, "Ahora alguien tendrá que reconstruirla."),
]

TITULO_STR = "CANDY MATRIX"
# Paleta de caramelo para las letras, siguiendo los colores de las frutas.
_ORDEN_COLORES = (0, 5, 3, 1, 2, None, 4, 6, 0, 5, 3, 1)


# ==================== utilidades ====================
def _ease(t):
    """Arranca y termina suave."""
    t = max(0.0, min(1.0, t))
    return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2


def _ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _ease_out_back(t, s=1.9):
    """Pasa un poco de largo y vuelve: el 'rebote' de las letras al caer."""
    t = max(0.0, min(1.0, t))
    t -= 1
    return t * t * ((s + 1) * t + s) + 1


def _fase(t, desde, hasta):
    """Progreso 0..1 de t dentro de [desde, hasta]."""
    if hasta <= desde:
        return 1.0
    return max(0.0, min(1.0, (t - desde) / (hasta - desde)))


def _mezcla(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def _oscurecer(color, k):
    return tuple(int(c * k) for c in color)


_cache = {}


def _guardado(clave, fabrica):
    """Superficies caras se crean una vez y se reutilizan."""
    s = _cache.get(clave)
    if s is None:
        s = _cache[clave] = fabrica()
    return s


# Los resplandores van aparte y con presupuesto: los que cambian de tamaño o de
# intensidad (la chispa al encenderse, el pulso) generan una copia por cada
# escalón, y sin límite la caché pasaba de 40 MB, demasiado para el navegador.
# Se descartan los menos usados recientemente.
_halos = OrderedDict()
_PRESUPUESTO_PIXELES = 8_000_000  # ~32 MB a 32 bits por píxel
_pixeles_halos = 0


# ==================== luz ====================
def _gradiente_blanco(curva):
    """Gradiente radial blanco pequeño; se escala suavemente al tamaño pedido.
    Calcularlo píxel a píxel solo 64x64 y luego escalarlo es mucho más rápido
    que calcularlo al tamaño final, y el escalado suave no deja escalones."""
    def crear():
        n = 64
        s = pygame.Surface((n, n))
        c = (n - 1) / 2.0
        for y in range(n):
            for x in range(n):
                d = math.hypot(x - c, y - c) / c
                k = max(0.0, 1.0 - d) ** curva
                v = int(255 * k)
                s.set_at((x, y), (v, v, v))
        return s
    return _guardado(('grad', curva), crear)


def _halo(ancho, alto, color, curva):
    global _pixeles_halos
    s = pygame.transform.smoothscale(_gradiente_blanco(curva), (ancho, alto)).convert()
    s.fill(color, special_flags=pygame.BLEND_MULT)
    _pixeles_halos += ancho * alto
    while _pixeles_halos > _PRESUPUESTO_PIXELES and len(_halos) > 1:
        _, viejo = _halos.popitem(last=False)  # el más antiguo
        _pixeles_halos -= viejo.get_width() * viejo.get_height()
    return s


def _cuantizar(v):
    """Redondea un tamaño a escalones: finos si es pequeño (se notaría), gruesos
    si es grande (no se nota y ahorra copias en caché)."""
    paso = 2 if v < 24 else 8 if v < 120 else 24
    return max(paso, int(v) // paso * paso)


def _luz(destino, x, y, radio, color, intensidad=1.0, curva=2.0, alto=None, niveles=16):
    """Suma un resplandor (BLEND_ADD): sobre el fondo oscuro se ve como luz.

    `radio` es la mitad del ancho y `alto` la mitad del alto (si se da, el
    resplandor es una elipse: así se hacen las estelas del destello).
    La intensidad se redondea a `niveles` escalones para acotar la caché.
    """
    k = int(intensidad * niveles + 0.5)
    if k <= 0 or radio <= 0:
        return
    if k > niveles:
        k = niveles
    rx = _cuantizar(radio)
    ry = rx if alto is None else _cuantizar(alto)
    # Se consulta la caché por los parámetros, sin calcular el color escalado:
    # esta función se llama cientos de veces por fotograma y en el caso común
    # (acierto) debe ser una sola búsqueda en un diccionario.
    clave = (rx, ry, color, k, niveles, curva)
    h = _halos.get(clave)
    if h is None:
        h = _halos[clave] = _halo(rx * 2, ry * 2, _oscurecer(color, k / niveles), curva)
    destino.blit(h, (int(x - rx), int(y - ry)), None, pygame.BLEND_ADD)


# ==================== escenario ====================
def _fondo():
    """Cielo nocturno violeta, nebulosas tenues y viñeta. Se dibuja una vez."""
    def crear():
        s = pygame.Surface((ANCHO, ALTO))
        arriba, abajo = (24, 14, 46), (5, 4, 13)
        for y in range(ALTO):
            pygame.draw.line(s, _mezcla(arriba, abajo, y / (ALTO - 1)), (0, y), (ANCHO, y))
        for x, y, r, color in ((260, 250, 360, (58, 18, 74)),
                               (960, 540, 420, (16, 34, 84)),
                               (700, 130, 280, (66, 22, 44))):
            _luz(s, x, y, r, color, 1.0, curva=1.6, niveles=1)
        s.blit(_vineta(), (0, 0))
        return s.convert()
    return _guardado('fondo', crear)


def _estrella(radio, nivel):
    return _guardado(('estrella', radio, nivel),
                     lambda: _halo(radio * 2, radio * 2, _oscurecer((190, 200, 255), nivel / 8), 3.0))


def _vineta():
    """Bordes oscurecidos, que centran la mirada."""
    n_x, n_y = 48, 32
    pequena = pygame.Surface((n_x, n_y), pygame.SRCALPHA)
    for y in range(n_y):
        for x in range(n_x):
            dx = (x - (n_x - 1) / 2) / ((n_x - 1) / 2)
            dy = (y - (n_y - 1) / 2) / ((n_y - 1) / 2)
            d = min(1.0, math.hypot(dx * 0.85, dy))
            pequena.set_at((x, y), (0, 0, 0, int(215 * d ** 2.4)))
    return pygame.transform.smoothscale(pequena, (ANCHO, ALTO))


_TIRA_V = None
_TIRA_H = None
_XS_RETICULA = list(range(CX % 48, ANCHO, 48))
_YS_RETICULA = list(range(CY % 48, ALTO, 48))


def _reticula(destino, intensidad):
    """Cuadrícula tenue: el motivo de 'matriz' que se ilumina al completarse.

    Se dibuja como tiras de 1 px sumadas (BLEND_ADD). La primera versión era una
    superficie de pantalla completa con alfa por píxel más alfa global: costaba
    17,7 ms por fotograma, todo el presupuesto de 60 fps. Así cuesta ~1,5 ms.
    """
    global _TIRA_V, _TIRA_H
    if intensidad <= 0:
        return
    if _TIRA_V is None:
        _TIRA_V = pygame.Surface((1, ALTO)).convert()
        _TIRA_H = pygame.Surface((ANCHO, 1)).convert()
    color = _oscurecer((120, 96, 210), min(1.0, intensidad))
    _TIRA_V.fill(color)
    _TIRA_H.fill(color)
    add = pygame.BLEND_ADD
    destino.blits([(_TIRA_V, (x, 0), None, add) for x in _XS_RETICULA], False)
    destino.blits([(_TIRA_H, (0, y), None, add) for y in _YS_RETICULA], False)


_TIRA_VELO = None


def _velo(destino, gris, modo):
    """Oscurece (BLEND_MULT) o ilumina (BLEND_ADD) toda la pantalla.

    Una capa de pantalla completa con alfa costaba 6,2 ms; multiplicar por una
    tira de 1200x100 reutilizada, repetida 8 veces, cuesta la mitad, y sumar,
    un cuarto. (Hacerlo con `fill(..., BLEND_MULT)` es peor: 49 ms.)
    """
    global _TIRA_VELO
    if _TIRA_VELO is None:
        _TIRA_VELO = pygame.Surface((ANCHO, 100)).convert()
    _TIRA_VELO.fill(gris)
    destino.blits([(_TIRA_VELO, (0, y), None, modo) for y in range(0, ALTO, 100)], False)


def _oscurecer_todo(destino, factor):
    """factor 1 = sin cambio, 0 = negro."""
    v = int(255 * max(0.0, min(1.0, factor)))
    if v < 255:
        _velo(destino, (v, v, v), pygame.BLEND_MULT)


def _iluminar_todo(destino, cantidad, color=(255, 246, 236)):
    """cantidad 0..1: destello que satura hacia `color`."""
    if cantidad > 0:
        _velo(destino, _oscurecer(color, min(1.0, cantidad)), pygame.BLEND_ADD)


# ==================== fichas ====================
def _ficha(valor, lado=46):
    """Ficha de caramelo con su número: sombra, brillo superior y borde."""
    def crear():
        color = COLOR_MAP[valor]
        s = pygame.Surface((lado, lado + 4), pygame.SRCALPHA)
        cuerpo = pygame.Rect(0, 0, lado, lado)
        pygame.draw.rect(s, (*_oscurecer(color, 0.45), 255), cuerpo.move(0, 4), border_radius=12)
        pygame.draw.rect(s, (*color, 255), cuerpo, border_radius=12)
        brillo = pygame.Rect(4, 3, lado - 8, int(lado * 0.42))
        pygame.draw.rect(s, (255, 255, 255, 72), brillo, border_radius=9)
        pygame.draw.rect(s, (*_oscurecer(color, 0.62), 255), cuerpo, 2, border_radius=12)
        f = fuente(TITULO, int(lado * 0.56))
        sombra = f.render(str(valor), True, _oscurecer(color, 0.4))
        num = f.render(str(valor), True, (255, 255, 255))
        s.blit(sombra, sombra.get_rect(center=(lado // 2, lado // 2 + 2)))
        s.blit(num, num.get_rect(center=(lado // 2, lado // 2)))
        return s
    return _guardado(('ficha', valor, lado), crear)


def _ficha_girada(valor, angulo, lado=46):
    """Las rotaciones se guardan en escalones de 6°, suficiente a esta velocidad."""
    paso = int(round(angulo / 6.0)) * 6 % 360
    if paso == 0:
        return _ficha(valor, lado)
    return _guardado(('ficha_g', valor, lado, paso),
                     lambda: pygame.transform.rotozoom(_ficha(valor, lado), paso, 1.0))


def _dibujar_ficha(destino, valor, x, y, alpha=255, angulo=0.0, lado=46, brillo=0.0):
    if alpha <= 0:
        return
    if brillo > 0:
        _luz(destino, x, y, lado * 0.95, COLOR_MAP[valor], brillo, curva=2.2)
    s = _ficha_girada(valor, angulo, lado)
    s.set_alpha(max(0, min(255, int(alpha))))
    destino.blit(s, s.get_rect(center=(int(x), int(y))))


# ==================== textos ====================
def _texto(cadena, tamano, color, archivo=TEXTO_FUERTE):
    return _guardado(('txt', cadena, tamano, color, archivo),
                     lambda: fuente(archivo, tamano).render(cadena, True, color))


def _penumbra(destino, x, y, rx, ry, fuerza):
    """Oscurece suavemente una elipse (BLEND_MULT), sin capa con alfa: se usa
    detrás de los subtítulos para que se lean aunque pasen fichas por detrás."""
    nivel = int(fuerza * 8 + 0.5)
    if nivel <= 0:
        return
    def crear():
        g = pygame.transform.smoothscale(_gradiente_blanco(1.3), (rx * 2, ry * 2)).convert()
        g.fill(_oscurecer((255, 255, 255), 0.72 * nivel / 8), special_flags=pygame.BLEND_MULT)
        blanco = pygame.Surface((rx * 2, ry * 2)).convert()
        blanco.fill((255, 255, 255))
        blanco.blit(g, (0, 0), None, pygame.BLEND_SUB)
        return blanco
    sup = _guardado(('penumbra', rx, ry, nivel), crear)
    destino.blit(sup, (x - rx, y - ry), None, pygame.BLEND_MULT)


def _dibujar_narracion(destino, cadena, k_aparicion, y):
    """Subtítulo de cine: con sombra suave, aparece subiendo unos píxeles."""
    if k_aparicion <= 0:
        return
    _penumbra(destino, CX, y, 520, 46, k_aparicion)
    alpha = int(255 * k_aparicion)
    dy = int(10 * (1 - _ease_out(k_aparicion)))
    sombra = _texto(cadena, 27, (0, 0, 0))
    frente = _texto(cadena, 27, (244, 236, 226))
    sombra.set_alpha(int(alpha * 0.7))
    frente.set_alpha(alpha)
    r = frente.get_rect(center=(CX, y + dy))
    destino.blit(sombra, r.move(0, 2))
    destino.blit(frente, r)


# ==================== título ====================
def _letra(c, color, tamano=104):
    """Letra de caramelo: contorno grueso, sombra caída y brillo superior."""
    def crear():
        f = fuente(TITULO, tamano)
        base = f.render(c, True, color)
        contorno_col = _oscurecer(color, 0.42)
        contorno = f.render(c, True, contorno_col)
        sombra = f.render(c, True, (16, 8, 26))
        g = 4  # grosor del contorno
        w, h = base.get_width() + 2 * g + 2, base.get_height() + 2 * g + 10
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        sombra.set_alpha(150)
        s.blit(sombra, (g, g + 8))
        for dx in range(-g, g + 1, 2):
            for dy in range(-g, g + 1, 2):
                if dx * dx + dy * dy <= g * g + 2:
                    s.blit(contorno, (g + dx, g + dy))
        s.blit(base, (g, g))
        # Brillo en la mitad superior, recortado a la forma de la letra: el
        # mínimo con la letra deja alfa 0 fuera de ella, y luego se pasa a blanco.
        banda = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(banda, (255, 255, 255, 80),
                         (0, 0, base.get_width(), int(base.get_height() * 0.48)))
        banda.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        banda.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_MAX)
        s.blit(banda, (g, g))
        return s
    return _guardado(('letra', c, color, tamano), crear)


def _colores_titulo():
    colores = []
    for idx in _ORDEN_COLORES:
        colores.append(None if idx is None else COLOR_MAP[idx])
    return colores


def _maqueta_titulo(tamano=104, espacio_extra=4):
    """Posición x de cada letra (respetando el ancho real de la fuente) y el
    título compuesto completo, que se usa una vez que todas han caído."""
    def crear():
        f = fuente(TITULO, tamano)
        colores = _colores_titulo()
        xs = []
        for i in range(len(TITULO_STR)):
            xs.append(f.size(TITULO_STR[:i])[0] + i * espacio_extra)
        letras = []
        for i, c in enumerate(TITULO_STR):
            if c == ' ':
                letras.append(None)
                continue
            letras.append(_letra(c, colores[i], tamano))
        ancho = xs[-1] + letras[-1].get_width()  # borde derecho real de la última letra
        alto = max(l.get_height() for l in letras if l)
        compuesto = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        for i, l in enumerate(letras):
            if l:
                compuesto.blit(l, (xs[i], 0))
        mascara = compuesto.copy()
        mascara.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_MAX)
        return xs, letras, compuesto, mascara
    return _guardado(('titulo', tamano), crear)


# ==================== partículas ====================
TAMANOS_PARTICULA = (4, 6, 8)
COLORES_BRASA = ((255, 200, 120), (255, 150, 200), (255, 230, 170))
COLORES_PARTICULA = tuple(COLOR_MAP) + COLORES_BRASA + ((255, 210, 230),)
class _Particulas:
    """Chispas y brasas dibujadas como luz sumada: cientos cuestan poco
    porque no se crea ninguna superficie al dibujarlas."""

    def __init__(self):
        self.lista = []

    def estallido(self, x, y, color, cantidad, velocidad, vida=0.8, radios=(6, 8), gravedad=140):
        for _ in range(cantidad):
            a = random.uniform(0, math.tau)
            v = random.uniform(velocidad * 0.3, velocidad)
            self.lista.append([x, y, math.cos(a) * v, math.sin(a) * v, 0.0,
                               random.uniform(vida * 0.6, vida), color,
                               random.choice(radios), gravedad])

    def brasa(self, x, y, color):
        self.lista.append([x + random.uniform(-14, 14), y + random.uniform(-6, 6),
                           random.uniform(-18, 18), random.uniform(-70, -30), 0.0,
                           random.uniform(1.2, 2.2), color, random.choice(TAMANOS_PARTICULA), -10])

    def actualizar_y_dibujar(self, destino, dt):
        vivas = []
        for p in self.lista:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            p[2] *= 0.985
            p[3] += p[8] * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            k = 1 - p[4] / p[5]
            _luz(destino, p[0], p[1], p[7], p[6], k, curva=2.6)
            if k > 0.35:
                destino.set_at((int(p[0]), int(p[1])), (255, 250, 235))
            vivas.append(p)
        self.lista = vivas


# ==================== escena ====================
class _Escena:
    """Estado de toda la cinemática; cada método dibuja una escena."""

    def __init__(self, sonido):
        self.sonido = sonido
        self.rng = random.Random(7)  # mismo cielo y mismas grietas cada vez
        self.particulas = _Particulas()
        self.hechos = set()  # eventos de una sola vez (sonidos, estallidos)

        grid_w = GRID * CELDA
        self.gx0 = CX - grid_w // 2
        self.gy0 = CY - grid_w // 2
        self.fichas = []
        for i in range(GRID):
            for j in range(GRID):
                destino = (self.gx0 + j * CELDA + CELDA // 2, self.gy0 + i * CELDA + CELDA // 2)
                # Repartidas por toda la pantalla salvo una franja central,
                # para que se note que vienen de lejos.
                while True:
                    inicio = (self.rng.uniform(60, ANCHO - 60), self.rng.uniform(FRANJA + 30, ALTO - FRANJA - 30))
                    if math.hypot(inicio[0] - CX, inicio[1] - CY) > 230:
                        break
                ang_salida = math.atan2(destino[1] - CY, destino[0] - CX) + self.rng.uniform(-0.35, 0.35)
                self.fichas.append({
                    'valor': self.rng.randrange(len(COLOR_MAP)),
                    'inicio': inicio,
                    'destino': destino,
                    'retraso': self.rng.uniform(0.0, 0.7),
                    'giro0': self.rng.uniform(-40, 40),
                    'bob': self.rng.uniform(0, math.tau),
                    'arco': self.rng.uniform(-90, 90),
                    'salida': ang_salida,
                    'dist_salida': self.rng.uniform(520, 760),
                    'giro_salida': self.rng.uniform(-540, 540),
                    'llego': False,
                })

        self.estrellas = [{
            'x': self.rng.uniform(0, ANCHO), 'y': self.rng.uniform(0, ALTO),
            'r': self.rng.choice((3, 4, 6)), 'fase': self.rng.uniform(0, math.tau),
            'vel': self.rng.uniform(0.6, 2.0), 'brillo': self.rng.uniform(0.25, 0.75),
        } for _ in range(120)]

        self.grietas = []
        for k in range(9):
            ang = k * math.tau / 9 + self.rng.uniform(-0.25, 0.25)
            x, y = CX, CY
            puntos = [(x, y)]
            for _ in range(self.rng.randint(6, 9)):
                ang += self.rng.uniform(-0.55, 0.55)
                largo = self.rng.uniform(18, 34)
                x += math.cos(ang) * largo
                y += math.sin(ang) * largo
                puntos.append((x, y))
            self.grietas.append(puntos)

        self.orbitas = [{
            'valor': self.rng.randrange(len(COLOR_MAP)),
            'radio': self.rng.uniform(170, 300), 'fase': self.rng.uniform(0, math.tau),
            'vel': self.rng.uniform(0.5, 1.1) * self.rng.choice((-1, 1)),
            'aplanado': self.rng.uniform(0.38, 0.55),
        } for _ in range(12)]

        self.lienzo = pygame.Surface((ANCHO, ALTO))

    # ---------- utilidades de escena ----------
    def sonar(self, nombre, clave):
        if clave in self.hechos:
            return
        self.hechos.add(clave)
        if self.sonido:
            self.sonido.play(nombre)

    def una_vez(self, clave):
        if clave in self.hechos:
            return False
        self.hechos.add(clave)
        return True

    def dibujar_cielo(self, s, t, brillo=1.0):
        s.blit(_fondo(), (0, 0))
        # 120 estrellas en una sola llamada (blits): una por una, la sobrecarga
        # de Python costaba ~6 ms por fotograma; así, ~0,3 ms.
        lote = []
        sen = math.sin
        for e in self.estrellas:
            # deriva lenta: las más grandes (más cercanas) se mueven más
            x = (e['x'] - t * e['r'] * 1.6) % ANCHO
            k = int(8 * e['brillo'] * (0.55 + 0.45 * sen(t * e['vel'] + e['fase'])) * brillo + 0.5)
            if k > 0:
                sprite = _estrella(e['r'], min(8, k))
                lote.append((sprite, (int(x) - e['r'], int(e['y']) - e['r']), None, pygame.BLEND_ADD))
        s.blits(lote, False)

    # ---------- escenas ----------
    def fragmentos_y_convergencia(self, s, t):
        _reticula(s, 0.055 * _fase(t, T_APERTURA, T_FRAGMENTOS))
        for f in self.fichas:
            aparicion = _fase(t, T_APERTURA + f['retraso'] * 1.6, T_APERTURA + f['retraso'] * 1.6 + 0.9)
            p = _ease(_fase(t, T_FRAGMENTOS + f['retraso'] * 0.7,
                            T_FRAGMENTOS + f['retraso'] * 0.7 + 1.15))
            bob = 7 * math.sin(t * 2.2 + f['bob']) * (1 - p)
            for retroceso, alpha_estela in ((0.10, 40), (0.05, 80)) if 0 < p < 1 else ():
                q = _ease(max(0.0, p - retroceso))
                x, y = self._camino(f, q)
                _dibujar_ficha(s, f['valor'], x, y, alpha_estela * aparicion, f['giro0'] * (1 - q))
            x, y = self._camino(f, p)
            _dibujar_ficha(s, f['valor'], x, y + bob, 255 * aparicion, f['giro0'] * (1 - p),
                           brillo=0.35 * aparicion)
            if p >= 1 and not f['llego']:
                f['llego'] = True
                self.particulas.estallido(x, y, COLOR_MAP[f['valor']], 5, 110, vida=0.45, radios=(4, 6))

    def _camino(self, f, p):
        """De la posición suelta a su celda, por un arco suave (no en línea recta)."""
        (x0, y0), (x1, y1) = f['inicio'], f['destino']
        x = x0 + (x1 - x0) * p
        y = y0 + (y1 - y0) * p
        arco = math.sin(math.pi * p) * f['arco']
        dx, dy = x1 - x0, y1 - y0
        largo = math.hypot(dx, dy) or 1
        return x - dy / largo * arco, y + dx / largo * arco

    def matriz(self, s, t, temblor=0.0, grietas=0.0, apagado=0.0):
        k = _fase(t, T_CONVERGENCIA, T_CONVERGENCIA + 0.6)
        respiracion = 0.5 + 0.5 * math.sin(t * 2.4)
        _reticula(s, (0.055 + 0.16 * k * (0.6 + 0.4 * respiracion)) * (1 - apagado))
        _luz(s, CX, CY, 300, (120, 70, 40), (0.45 + 0.15 * respiracion) * k * (1 - apagado),
             curva=1.8, niveles=6)

        # Onda de luz al completarse
        p_onda = _fase(t, T_CONVERGENCIA, T_CONVERGENCIA + 1.1)
        if 0 < p_onda < 1:
            r = int(170 + 620 * _ease_out(p_onda))
            col = _mezcla((255, 236, 200), (24, 14, 46), p_onda)
            for g in range(3):
                pygame.gfxdraw.aacircle(s, CX, CY, r + g, col)
            if self.una_vez('onda'):
                self.sonar('chime', 'chime_matriz')
                for f in self.fichas:
                    self.particulas.estallido(*f['destino'], COLOR_MAP[f['valor']], 2, 160, vida=0.6, radios=(4,))

        for f in self.fichas:
            x, y = f['destino']
            if temblor:
                d = math.hypot(x - CX, y - CY)
                amp = temblor * max(0.0, 1 - d / 260) * 4
                x += random.uniform(-amp, amp)
                y += random.uniform(-amp, amp)
            _dibujar_ficha(s, f['valor'], x, y, 255, 0, brillo=(0.25 + 0.2 * respiracion) * (1 - apagado))

        self._corchetes(s, k, 1 - apagado)

        if grietas > 0:
            for puntos in self.grietas:
                n = max(1, int(round(grietas * (len(puntos) - 1))))
                tramo = puntos[:n + 1]
                if len(tramo) >= 2:
                    pygame.draw.lines(s, (150, 30, 70), False, tramo, 6)
                    pygame.draw.lines(s, (255, 214, 236), False, tramo, 2)

    def _corchetes(self, s, k, alpha_k=1.0, separacion=0.0):
        """Los corchetes de matriz [ ]: crecen desde el centro hacia afuera."""
        if k <= 0 or alpha_k <= 0:
            return
        alto_total = GRID * CELDA + 20
        mitad = int(alto_total / 2 * _ease_out(k))
        color = _mezcla((24, 14, 46), (246, 236, 222), alpha_k)
        for lado in (-1, 1):
            x = CX + lado * (GRID * CELDA // 2 + 20 + separacion)
            pygame.draw.line(s, color, (x, CY - mitad), (x, CY + mitad), 6)
            if k > 0.6:
                serif = int(16 * _fase(k, 0.6, 1.0))
                for y in (CY - mitad, CY + mitad):
                    pygame.draw.line(s, color, (x, y), (x - lado * serif, y), 6)

    def vacio(self, s, t):
        """El Vacío emerge en el centro y agrieta la matriz."""
        p = _fase(t, T_MATRIZ, T_VACIO)
        self.matriz(s, t, temblor=p, grietas=_ease(_fase(t, T_MATRIZ + 0.5, T_VACIO - 0.1)),
                    apagado=0.5 * p)
        _oscurecer_todo(s, 1 - 0.35 * p)

        r = int(14 + 58 * _ease_out(_fase(t, T_MATRIZ + 0.2, T_MATRIZ + 1.4)))
        pulso = 0.5 + 0.5 * math.sin(t * 7)
        _luz(s, CX, CY, r * 2.6, (150, 18, 70), 0.7 + 0.3 * pulso, curva=1.6, niveles=8)
        pygame.gfxdraw.filled_circle(s, CX, CY, r, (6, 2, 10))
        pygame.gfxdraw.aacircle(s, CX, CY, r, (210, 50, 100))
        pygame.gfxdraw.aacircle(s, CX, CY, r - 1, (120, 20, 60))
        cero = _texto("0", max(12, int(r * 1.15) // 4 * 4), (238, 60, 96), TITULO)
        s.blit(cero, cero.get_rect(center=(CX, CY + 2)))
        self.sonar('error', 'error_vacio')

    def ruptura(self, s, t):
        p = _fase(t, T_VACIO, T_RUPTURA)
        if self.una_vez('estallido'):
            self.sonar('shatter', 'shatter')
            for f in self.fichas:
                self.particulas.estallido(*f['destino'], COLOR_MAP[f['valor']], 3, 380, vida=1.0)
            self.particulas.estallido(CX, CY, (255, 210, 230), 26, 520, vida=1.1, radios=(4, 6, 8))

        _reticula(s, 0.12 * (1 - p))

        # El Vacío implota y desaparece
        r = int(72 * (1 - _ease_out(_fase(t, T_VACIO, T_VACIO + 0.45))))
        if r > 2:
            _luz(s, CX, CY, r * 2.4, (150, 18, 70), 0.8, curva=1.6, niveles=8)
            pygame.gfxdraw.filled_circle(s, CX, CY, r, (6, 2, 10))
        p_anillo = _fase(t, T_VACIO, T_VACIO + 0.8)
        if p_anillo < 1:
            rr = int(60 + 640 * _ease_out(p_anillo))
            col = _mezcla((255, 120, 170), (14, 8, 26), p_anillo)
            for g in range(4):
                pygame.gfxdraw.aacircle(s, CX, CY, rr + g, col)

        q = _ease_out(_fase(t, T_VACIO, T_VACIO + 1.9))
        for f in self.fichas:
            # Una sola estela: con 36 fichas girando, cada copia extra son 36
            # rotaciones y mezclas más en el fotograma más cargado.
            for retroceso, alpha_estela in ((0.06, 80),):
                qq = max(0.0, q - retroceso)
                x, y = self._salida(f, qq)
                _dibujar_ficha(s, f['valor'], x, y, alpha_estela * (1 - qq) ** 1.3, f['giro_salida'] * qq)
            x, y = self._salida(f, q)
            _dibujar_ficha(s, f['valor'], x, y, 255 * (1 - q) ** 1.3, f['giro_salida'] * q,
                           brillo=0.4 * (1 - q))
        self._corchetes(s, 1.0, 1 - _fase(t, T_VACIO, T_VACIO + 0.7), separacion=420 * q)

    def _salida(self, f, q):
        x0, y0 = f['destino']
        d = f['dist_salida'] * q
        return x0 + math.cos(f['salida']) * d, y0 + math.sin(f['salida']) * d

    def chispa(self, s, t, dt):
        """El Aprendiz: una luz cálida que atrae de vuelta los fragmentos."""
        ignicion = _fase(t, T_RUPTURA + 0.15, T_RUPTURA + 0.8)
        if ignicion <= 0:
            return
        self.sonar('chime', 'chime_chispa')
        crece = _ease_out_back(ignicion, 1.4)
        pulso = 1 + 0.12 * math.sin(t * 3.4)

        # Destello en cruz con una estela horizontal larga, como el reflejo de
        # una lente de cine. (Los resplandores son elipses alineadas con los
        # ejes, así que rayos diagonales saldrían como manchas: la cruz no.)
        respira = 0.5 + 0.5 * math.sin(t * 1.9)
        _luz(s, CX, CY, (300 + 50 * respira) * crece, (255, 150, 90), 0.5 * crece,
             curva=2.2, alto=5, niveles=8)
        _luz(s, CX, CY, 92 * crece, (255, 214, 160), 0.8 * crece, curva=1.8, alto=3, niveles=8)
        _luz(s, CX, CY, 3, (255, 214, 160), 0.7 * crece, curva=1.8, alto=(110 + 30 * respira) * crece,
             niveles=8)

        _luz(s, CX, CY, 250 * crece, (96, 40, 130), 0.55, curva=1.7, niveles=6)
        _luz(s, CX, CY, 120 * crece * pulso, (255, 160, 70), 0.85, curva=2.0, niveles=8)
        _luz(s, CX, CY, 44 * crece * pulso, (255, 238, 205), 1.0, curva=1.6, niveles=8)
        pygame.gfxdraw.filled_circle(s, CX, CY, max(1, int(7 * crece)), (255, 252, 242))
        pygame.gfxdraw.aacircle(s, CX, CY, max(1, int(7 * crece)), (255, 252, 242))

        # Fragmentos que vuelven, en órbitas que se cierran poco a poco
        atraccion = _ease(_fase(t, T_RUPTURA + 0.4, T_CHISPA))
        for o in self.orbitas:
            radio = o['radio'] * (1 - 0.45 * atraccion)
            ang = o['fase'] + t * o['vel']
            x = CX + math.cos(ang) * radio
            y = CY + math.sin(ang) * radio * o['aplanado']
            delante = math.sin(ang) > 0
            alpha = 255 * _fase(t, T_RUPTURA + 0.4, T_RUPTURA + 1.2) * (1.0 if delante else 0.55)
            _dibujar_ficha(s, o['valor'], x, y, alpha, 0, lado=26, brillo=0.3)

        if random.random() < 0.55:
            self.particulas.brasa(CX, CY, random.choice(COLORES_BRASA))

    def titulo(self, s, t, dt):
        p_subida = _fase(t, T_CHISPA, T_CHISPA + 0.5)
        y_titulo = CY - 38
        if p_subida < 1:
            # La chispa sube hasta donde aparecerá el título
            y = CY + (y_titulo - CY) * _ease(p_subida)
            _luz(s, CX, y, 60 + 200 * p_subida, (255, 200, 150), 0.9, curva=1.8, niveles=8)

        xs, letras, compuesto, mascara = _maqueta_titulo()
        x0 = CX - compuesto.get_width() // 2
        y0 = y_titulo - compuesto.get_height() // 2
        inicio = T_CHISPA + 0.35

        luz_titulo = _fase(t, inicio, inicio + 1.2)
        _luz(s, CX, y_titulo + 10, 470, (150, 50, 110), 0.5 * luz_titulo, curva=1.7, alto=150, niveles=6)

        todas = True
        for i, letra in enumerate(letras):
            if letra is None:
                continue
            t_letra = inicio + i * 0.08
            p = _fase(t, t_letra, t_letra + 0.5)
            if p <= 0:
                todas = False
                continue
            if p < 1:
                todas = False
            y = y0 - 130 * (1 - _ease_out_back(p))
            letra.set_alpha(int(255 * min(1.0, p * 2.5)))
            s.blit(letra, (x0 + xs[i], y))
            if p >= 1 and self.una_vez(('letra', i)):
                self.sonar('explosion', ('pop', i))
                cx_l = x0 + xs[i] + letra.get_width() // 2
                color = COLOR_MAP[_ORDEN_COLORES[i]]
                self.particulas.estallido(cx_l, y0 + letra.get_height() // 2, color, 8, 260, vida=0.7)

        if todas:
            fin = inicio + (len(letras) - 1) * 0.08 + 0.5
            self.sonar('levelup', 'levelup')
            p_brillo = _fase(t, fin + 0.15, fin + 0.95)
            if 0 < p_brillo < 1:
                self._destello(s, compuesto, mascara, x0, y0, p_brillo)
            k_sub = _fase(t, fin + 0.3, fin + 1.1)
            if k_sub > 0:
                sub = _texto("El conocimiento está en tus manos.", 28, (246, 232, 220))
                sub.set_alpha(int(255 * k_sub))
                s.blit(sub, sub.get_rect(center=(CX, y_titulo + 96 + 8 * (1 - _ease_out(k_sub)))))
            k_aviso = _fase(t, fin + 1.6, fin + 2.2)
            if k_aviso > 0:
                aviso = _texto("Toca la pantalla para continuar", 18, (200, 190, 214))
                aviso.set_alpha(int(255 * k_aviso * (0.55 + 0.45 * math.sin(t * 3.2))))
                s.blit(aviso, aviso.get_rect(center=(CX, ALTO - 70)))
            if random.random() < 0.25:
                self.particulas.brasa(random.uniform(CX - 380, CX + 380), y_titulo + 50,
                                      random.choice([COLOR_MAP[i] for i in (0, 3, 4, 6)]))

    def _destello(self, s, compuesto, mascara, x0, y0, p):
        """Una franja de luz cruza el título, recortada a la forma de las letras."""
        w, h = compuesto.get_size()
        banda = _guardado(('banda', w, h), lambda: pygame.Surface((w, h), pygame.SRCALPHA))
        banda.fill((0, 0, 0, 0))
        x = int(-160 + (w + 320) * _ease(p))
        pygame.draw.polygon(banda, (255, 255, 255, 170),
                            [(x, 0), (x + 70, 0), (x + 20, h), (x - 50, h)])
        banda.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(banda, (x0, y0))


# ==================== bucle ====================
_DESCARTE = pygame.Surface((1, 1))  # destino para precalentar la caché
async def mostrar_intro(ventana, sound=None):
    """Corre la cinemática una vez al arrancar. `sound` es el SoundManager ya
    creado (todavía sin música de fondo): cada momento de la historia dispara
    su propio efecto de sonido."""
    clock = pygame.time.Clock()
    escena = _Escena(sound)
    # Calentar las cachés antes de empezar, para que el primer segundo no
    # tartamudee mientras se crean el fondo y las fichas.
    _fondo()
    _maqueta_titulo()
    for v in range(len(COLOR_MAP)):
        _ficha(v)
        _ficha(v, 26)
    for curva in (1.6, 1.7, 1.8, 2.0, 2.2, 2.4, 2.6, 3.0):
        _gradiente_blanco(curva)
    # Rotaciones de las fichas y halos de las partículas: crearlos sobre la
    # marcha la primera vez que se necesitan causaba tirones de hasta 155 ms
    # justo en el estallido, que es el momento que más tiene que lucir.
    for v in range(len(COLOR_MAP)):
        for angulo in range(0, 360, 6):
            _ficha_girada(v, angulo)
            _ficha_girada(v, angulo, 26)
    for color in COLORES_PARTICULA:
        for r in TAMANOS_PARTICULA:
            for k in range(1, 17):
                _luz(_DESCARTE, 0, 0, r, color, k / 16, curva=2.6)

    # Descarta el toque/clic con el que el navegador arrancó el juego, que de
    # otro modo quedaría en la cola y saltaría la cinemática en el primer frame.
    pygame.event.clear()
    t0 = time.time()
    anterior = t0
    t_salida = None  # instante en que empezó el fundido final

    while True:
        ahora = time.time()
        t = ahora - t0
        dt = max(0.0, min(0.05, ahora - anterior))
        anterior = ahora

        for ev in entrada.obtener_eventos():
            if ev.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if (t_salida is None and t >= ESPERA_ANTES_DE_SALTAR
                    and ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN)):
                t_salida = t

        if t_salida is None and t >= TOTAL:
            t_salida = t
        if t_salida is not None and t - t_salida >= DURACION_SALIDA:
            ventana.fill((0, 0, 0))
            pygame.display.flip()
            return

        # Sacudida al estallar: solo entonces se dibuja en un lienzo aparte para
        # poder desplazarlo; el resto del tiempo se dibuja directo en la ventana
        # y se ahorra una copia de pantalla completa (~2,5 ms) por fotograma.
        sacudida = 18 * (1 - _fase(t, T_VACIO, T_VACIO + 0.8)) if T_VACIO <= t < T_VACIO + 0.8 else 0
        s = escena.lienzo if sacudida else ventana
        apagar_cielo = 0.55 if T_VACIO <= t < T_CHISPA else 1.0
        escena.dibujar_cielo(s, t, apagar_cielo)

        if t < T_CONVERGENCIA:
            escena.fragmentos_y_convergencia(s, t)
        elif t < T_MATRIZ:
            escena.matriz(s, t)
        elif t < T_VACIO:
            escena.vacio(s, t)
        elif t < T_RUPTURA:
            escena.ruptura(s, t)
        elif t < T_CHISPA:
            escena.chispa(s, t, dt)
        else:
            escena.titulo(s, t, dt)

        escena.particulas.actualizar_y_dibujar(s, dt)

        if sacudida:
            ventana.fill((0, 0, 0))
            ventana.blit(s, (int(random.uniform(-sacudida, sacudida)),
                             int(random.uniform(-sacudida, sacudida))))

        # Subtítulos (fuera de la sacudida, para que se lean)
        y_sub = ALTO - FRANJA - 44
        for desde, hasta, cadena in NARRACION:
            if desde <= t <= hasta:
                k = min(_fase(t, desde, desde + 0.5), 1 - _fase(t, hasta - 0.45, hasta))
                _dibujar_narracion(ventana, cadena, k, y_sub)

        # Franjas de cine: entran al empezar y se abren para el título
        franja = int(FRANJA * _ease(_fase(t, 0.0, 0.8)) * (1 - _ease(_fase(t, T_CHISPA, T_CHISPA + 0.8))))
        if franja > 0:
            ventana.fill((0, 0, 0), (0, 0, ANCHO, franja))
            ventana.fill((0, 0, 0), (0, ALTO - franja, ANCHO, franja))
            if t >= 1.6 and t_salida is None and franja >= FRANJA - 2:
                saltar = _texto("Saltar  ›", 17, (150, 140, 170))
                ventana.blit(saltar, saltar.get_rect(midright=(ANCHO - 26, franja // 2)))

        # Destello blanco al estallar y al nacer el título
        for inicio_destello, fuerza in ((T_VACIO, 0.9), (T_CHISPA + 0.3, 0.75)):
            k = _fase(t, inicio_destello, inicio_destello + 0.45)
            if 0 < k < 1:
                _iluminar_todo(ventana, fuerza * (1 - k) ** 2)

        # Fundido de entrada y de salida
        negro = 0.0
        if t < T_APERTURA:
            negro = 1 - _ease(t / T_APERTURA)
        if t_salida is not None:
            negro = max(negro, _ease((t - t_salida) / DURACION_SALIDA))
        if negro > 0:
            _oscurecer_todo(ventana, 1 - negro)

        pygame.display.flip()
        clock.tick(Config.FPS)
        await asyncio.sleep(0)
