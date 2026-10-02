# entrada.py
"""Traduce los toques de pantalla a eventos de ratón.

En el navegador de un celular o tablet SDL **no** entrega los toques como
clics: los manda como `FINGERDOWN` / `FINGERUP` / `FINGERMOTION`, y con las
coordenadas normalizadas entre 0 y 1 en vez de píxeles. Como todo el juego está
escrito contra `MOUSEBUTTONDOWN` y `ev.pos`, en el celular no respondía nada:
ni los botones, ni el teclado en pantalla, ni el tablero.

La traducción se hace aquí, una sola vez, en el punto por donde entran todos los
eventos. Así el resto del código sigue hablando de clics y no necesita saber si
hubo un dedo o un ratón, y no hay trece bucles de eventos que mantener en
sincronía. Traducir también `FINGERUP` conserva el gesto de arrastrar para
intercambiar fichas en el match-3, que usa el par pulsar/soltar.
"""
import pygame

from config import Config

# Última posición tocada mientras el dedo sigue apoyado; None si el jugador está
# usando un ratón de verdad. Ver posicion_puntero().
_tactil = None

_EQUIVALENCIA = {
    pygame.FINGERDOWN: pygame.MOUSEBUTTONDOWN,
    pygame.FINGERUP: pygame.MOUSEBUTTONUP,
    pygame.FINGERMOTION: pygame.MOUSEMOTION,
}

_EVENTOS_RATON = (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)


def _a_pixeles(ev):
    """Convierte las coordenadas normalizadas (0..1) de un toque a píxeles."""
    superficie = pygame.display.get_surface()
    ancho, alto = superficie.get_size() if superficie else (Config.ANCHO, Config.ALTO)
    return (int(ev.x * ancho), int(ev.y * alto))


def obtener_eventos():
    """`pygame.event.get()` con los toques convertidos en eventos de ratón."""
    global _tactil
    salida = []

    for ev in pygame.event.get():
        # Algunas plataformas ya sintetizan un clic por cada toque. Se descartan
        # para no procesar el mismo toque dos veces: los FINGER* son la única
        # fuente de verdad del táctil, en cualquier plataforma.
        if ev.type in _EVENTOS_RATON and getattr(ev, 'touch', False):
            continue

        if ev.type in _EQUIVALENCIA:
            pos = _a_pixeles(ev)
            tipo = _EQUIVALENCIA[ev.type]
            if tipo == pygame.MOUSEMOTION:
                nuevo = pygame.event.Event(tipo, pos=pos, rel=(0, 0),
                                           buttons=(1, 0, 0), touch=True)
            else:
                nuevo = pygame.event.Event(tipo, pos=pos, button=1, touch=True)
            # Al levantar el dedo ya no hay nada "bajo el cursor": si se
            # mantuviera, la tecla pulsada se quedaría resaltada para siempre.
            _tactil = None if ev.type == pygame.FINGERUP else pos
            salida.append(nuevo)
            continue

        if ev.type == pygame.MOUSEMOTION:
            _tactil = None  # hay un ratón de verdad en uso

        salida.append(ev)

    return salida


def posicion_puntero():
    """Dónde está el cursor, o el dedo mientras siga apoyado.

    `pygame.mouse.get_pos()` no se mueve con el dedo, así que en el celular
    ningún botón llegaría a verse resaltado y el jugador no tendría ninguna
    señal de que está tocando la tecla correcta.
    """
    return _tactil if _tactil is not None else pygame.mouse.get_pos()
