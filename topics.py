# topics.py
"""Registro central de temas de álgebra lineal disponibles en el Hub.

Cada tema reutiliza el mismo tablero tipo match-3, pero con su propio banco de
preguntas (quiz_system) y su propia Zona de Estudio (learn_zone). Los temas
marcados como no disponibles son el roadmap: se muestran en el Hub como
"Próximamente" para que el plan de expansión sea visible dentro del juego.
"""

TEMAS = [
    {'id': 'matrices', 'nombre': 'Matrices', 'color': (233, 90, 64),
     'resumen': 'Suma, determinante, rango y autovalores usando el tablero como matriz.',
     'disponible': True},
    {'id': 'vectores', 'nombre': 'Vectores', 'color': (60, 140, 200),
     'resumen': 'Suma, producto escalar y norma usando las filas del tablero como vectores.',
     'disponible': True},
    {'id': 'sistemas', 'nombre': 'Sistemas de ecuaciones', 'color': (150, 110, 200),
     'resumen': 'Encuentra el multiplicador k que elimina una incógnita: eliminación gaussiana jugable.',
     'disponible': True},
    {'id': 'espacios', 'nombre': 'Espacios vectoriales', 'color': (90, 160, 110),
     'resumen': 'Próximamente: base, dimensión e independencia lineal.',
     'disponible': False},
    {'id': 'transformaciones', 'nombre': 'Transformaciones lineales', 'color': (210, 150, 60),
     'resumen': 'Próximamente: rotaciones, escalados y autovectores en acción.',
     'disponible': False},
]

_POR_ID = {t['id']: t for t in TEMAS}


def tema(tema_id):
    return _POR_ID.get(tema_id, _POR_ID['matrices'])


def nombre(tema_id):
    return tema(tema_id)['nombre']


def disponible(tema_id):
    return tema(tema_id)['disponible']
