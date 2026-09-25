# progress.py
"""Progreso por estudiante y por tema, guardado en un JSON junto al proyecto
(varios estudiantes pueden usar el mismo computador sin mezclar su avance).
Además del mejor nivel/puntaje históricos, guarda el nivel más alto
desbloqueado por tema: así el mapa de niveles sabe qué está disponible."""
import json
import os

from config import Config

_RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'progreso_estudiante.json')

_VACIO = {'mejor_nivel': 0, 'mejor_puntaje': 0, 'partidas_jugadas': 0, 'nivel_desbloqueado': 1}


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


def _registro(datos, estudiante, tema_id):
    por_estudiante = datos.setdefault(estudiante, {})
    return por_estudiante.setdefault(tema_id, dict(_VACIO))


def registrar_resultado(estudiante, tema_id, nivel_alcanzado, puntaje):
    """Actualiza el progreso de un tema si el resultado nuevo mejora el mejor guardado."""
    datos = cargar()
    actual = _registro(datos, estudiante, tema_id)
    actual['partidas_jugadas'] = actual.get('partidas_jugadas', 0) + 1
    if (nivel_alcanzado, puntaje) > (actual.get('mejor_nivel', 0), actual.get('mejor_puntaje', 0)):
        actual['mejor_nivel'] = nivel_alcanzado
        actual['mejor_puntaje'] = puntaje
    guardar(datos)
    return actual


def desbloquear_nivel(estudiante, tema_id, nivel_completado):
    """Se llama al superar `nivel_completado`: desbloquea el siguiente,
    sin pasar nunca de Config.MAX_LEVEL."""
    datos = cargar()
    actual = _registro(datos, estudiante, tema_id)
    siguiente = min(Config.MAX_LEVEL, nivel_completado + 1)
    actual['nivel_desbloqueado'] = max(actual.get('nivel_desbloqueado', 1), siguiente)
    guardar(datos)
    return actual['nivel_desbloqueado']


def nivel_desbloqueado(estudiante, tema_id):
    return resumen(estudiante, tema_id).get('nivel_desbloqueado', 1)


def resumen(estudiante, tema_id):
    datos = cargar()
    return datos.get(estudiante, {}).get(tema_id, dict(_VACIO))
