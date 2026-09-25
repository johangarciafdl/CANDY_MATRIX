# animations.py
"""Máquina de estados de animación del tablero, al estilo Candy Crush.

Ciclo completo de una jugada:
    swap -> (sin combinación) swap_back -> idle
    swap -> (hay combinación) clear -> fall -> [clear -> fall ...] -> idle

La lógica del tablero solo se aplica cuando la animación correspondiente termina,
así lo que ve el jugador y lo que dice la matriz nunca se contradicen.
"""
import math
import pygame

from config import Config
from matrix_logic import buscar_combinaciones, intercambiar, aplicar_gravedad

DUR_SWAP = 0.16
DUR_CLEAR = 0.24
DUR_FALL_BASE = 0.16
DUR_FALL_POR_CELDA = 0.035


def _ahora():
    return pygame.time.get_ticks() / 1000.0


def _ease_in_out(t):
    """Arranca y termina suave: da el deslizamiento elástico del intercambio."""
    return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2


def _ease_caida(t):
    """Acelera como gravedad real y remata con un rebotecito al aterrizar."""
    if t < 0.86:
        u = t / 0.86
        return u * u
    u = (t - 0.86) / 0.14
    return 1 + 0.07 * math.sin(u * math.pi)


class BoardAnimator:
    def __init__(self, tablero):
        self.tablero = tablero
        self.estado = 'idle'
        self.t0 = 0.0
        self.dur = 0.0
        self.par = None
        self.limpiando = set()
        self.caidas = None
        self.cascada = 0
        self._pendientes = []

    # ---------- consultas ----------
    def ocupado(self):
        return self.estado != 'idle'

    def _progreso(self):
        if self.dur <= 0:
            return 1.0
        return min(1.0, (_ahora() - self.t0) / self.dur)

    # ---------- control ----------
    def reiniciar(self, tablero):
        self.tablero = tablero
        self.estado = 'idle'
        self.par = None
        self.limpiando = set()
        self.caidas = None
        self.cascada = 0
        self._pendientes = []

    def iniciar_habilidad(self, celdas, etiqueta=None):
        """Dispara la eliminación de un conjunto arbitrario de celdas (habilidades)."""
        celdas = {c for c in celdas if self.tablero[c[0]][c[1]] is not None}
        if self.ocupado() or not celdas:
            return False
        self.cascada = 1
        self._iniciar_clear(celdas)
        self._pendientes.append({'tipo': 'eliminadas', 'celdas': set(celdas),
                                 'cascada': 1, 'habilidad': etiqueta or 'Habilidad'})
        return True

    def iniciar_swap(self, p1, p2):
        """Arranca el intercambio. El tablero todavía no cambia."""
        if self.ocupado():
            return False
        self.par = (p1, p2)
        self.estado = 'swap'
        self.t0 = _ahora()
        self.dur = DUR_SWAP
        return True

    def _iniciar_clear(self, combinaciones):
        self.limpiando = set(combinaciones)
        self.estado = 'clear'
        self.t0 = _ahora()
        self.dur = DUR_CLEAR

    def update(self):
        """Avanza la animación. Devuelve los eventos ocurridos en este frame."""
        eventos = []
        if self._pendientes:
            eventos.extend(self._pendientes)
            self._pendientes = []
        if self.estado == 'idle' or self._progreso() < 1.0:
            return eventos

        if self.estado == 'swap':
            p1, p2 = self.par
            intercambiar(self.tablero, p1, p2)
            combinaciones = buscar_combinaciones(self.tablero)
            if combinaciones:
                self.cascada = 1
                self._iniciar_clear(combinaciones)
                eventos.append({'tipo': 'movimiento_valido'})
                eventos.append({'tipo': 'eliminadas', 'celdas': set(combinaciones), 'cascada': 1})
            else:
                self.estado = 'swap_back'
                self.t0 = _ahora()
                self.dur = DUR_SWAP
                eventos.append({'tipo': 'movimiento_invalido', 'par': (p1, p2)})

        elif self.estado == 'swap_back':
            intercambiar(self.tablero, *self.par)
            self.par = None
            self.estado = 'idle'
            eventos.append({'tipo': 'estable'})

        elif self.estado == 'clear':
            for (i, j) in self.limpiando:
                self.tablero[i][j] = None
            self.limpiando = set()
            self.par = None
            self.caidas = aplicar_gravedad(self.tablero)
            maxima = max((max(fila) for fila in self.caidas), default=0)
            self.estado = 'fall'
            self.t0 = _ahora()
            self.dur = DUR_FALL_BASE + DUR_FALL_POR_CELDA * maxima

        elif self.estado == 'fall':
            self.caidas = None
            combinaciones = buscar_combinaciones(self.tablero)
            if combinaciones:
                self.cascada += 1
                self._iniciar_clear(combinaciones)
                eventos.append({'tipo': 'eliminadas', 'celdas': set(combinaciones), 'cascada': self.cascada})
            else:
                self.cascada = 0
                self.estado = 'idle'
                eventos.append({'tipo': 'estable'})

        return eventos

    # ---------- datos para dibujar ----------
    def offset(self, i, j):
        """Desplazamiento en píxeles de la celda respecto de su posición base."""
        if self.estado in ('swap', 'swap_back') and self.par:
            p1, p2 = self.par
            t = _ease_in_out(self._progreso())
            c = Config.TAMANO_CELDA
            if (i, j) == p1:
                return ((p2[1] - p1[1]) * c * t, (p2[0] - p1[0]) * c * t)
            if (i, j) == p2:
                return ((p1[1] - p2[1]) * c * t, (p1[0] - p2[0]) * c * t)

        elif self.estado == 'fall' and self.caidas:
            distancia = self.caidas[i][j]
            if distancia:
                p = _ease_caida(self._progreso())
                return (0, -distancia * Config.TAMANO_CELDA * (1 - p))

        return (0, 0)

    def escala(self, i, j):
        """Escala de la celda: infla un poco y luego revienta al eliminarse."""
        if self.estado == 'clear' and (i, j) in self.limpiando:
            t = self._progreso()
            if t < 0.3:
                return 1 + 0.35 * (t / 0.3)
            return max(0.0, 1.35 * (1 - (t - 0.3) / 0.7))
        return 1.0
