# progress.py
"""Progreso del estudiante por tema, guardado en un JSON junto al proyecto para
que el Hub pueda mostrar el mejor nivel/puntaje sin depender de la partida activa."""
import json
import os

_RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'progreso_estudiante.json')


def cargar():
    if not os.path.exists(_RUTA):
        return {}
    try:
        with open(_RUTA, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def guardar(datos):
    try:
        with open(_RUTA, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def registrar_resultado(tema_id, nivel_alcanzado, puntaje):
    """Actualiza el progreso de un tema si el resultado nuevo mejora el mejor guardado."""
    datos = cargar()
    actual = datos.get(tema_id, {'mejor_nivel': 0, 'mejor_puntaje': 0, 'partidas_jugadas': 0})
    actual['partidas_jugadas'] = actual.get('partidas_jugadas', 0) + 1
    if (nivel_alcanzado, puntaje) > (actual.get('mejor_nivel', 0), actual.get('mejor_puntaje', 0)):
        actual['mejor_nivel'] = nivel_alcanzado
        actual['mejor_puntaje'] = puntaje
    datos[tema_id] = actual
    guardar(datos)
    return actual


def resumen(tema_id):
    datos = cargar()
    return datos.get(tema_id, {'mejor_nivel': 0, 'mejor_puntaje': 0, 'partidas_jugadas': 0})
