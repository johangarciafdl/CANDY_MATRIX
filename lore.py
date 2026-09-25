# lore.py
"""Lore de Matrixia, adaptado del GDD original (pensado para Unity) a este
proyecto en Python. Cada tema del Hub es un "continente" con un guardián que
tiene personalidad propia y un pequeño banco de frases por evento, para que el
juego se sienta como parte de una aventura y no solo una colección de
ejercicios. No hay motor de diálogos: estas frases se muestran con el mismo
banner de aviso que ya usa cada minijuego, en los momentos clave (entrada,
nivel superado, tiempo agotado)."""
import random

CONTINENTES = {
    'matrices': {
        'continente': 'Matricia',
        'guardian': 'Matra',
        'identidad': 'Rojo · estructuras cuadriculadas',
        'personalidad': 'Sabia, calmada',
        'entrada': ["Has llegado a Matricia. Aquí comienza tu verdadero viaje.",
                    "Antes de resolver el caos, aprende a encontrar su estructura."],
        'nivel': ["Exacto. Esa es la estructura.", "Bien visto: comienzas a dominarlo."],
        'tiempo_agotado': ["Casi. Observa nuevamente la posición.",
                            "No necesitas ir más rápido. Necesitas comprender qué está fallando."],
    },
    'vectores': {
        'continente': 'Vectoria',
        'guardian': 'Vektor',
        'identidad': 'Verde · mundo espacial',
        'personalidad': 'Reflexivo, aventurero',
        'entrada': ["Has llegado a Vectoria. No basta con saber cuánto avanzas.",
                    "Debes saber hacia dónde."],
        'nivel': ["Exacto: esa dirección era la correcta.", "Tu razonamiento está tomando forma."],
        'tiempo_agotado': ["Casi. Revisa la dirección de tus vectores.",
                            "No necesitas ir más rápido. Necesitas comprender qué está fallando."],
    },
    'sistemas': {
        'continente': 'Ecuaria',
        'guardian': 'Equis',
        'identidad': 'Amarillo · caminos y torres',
        'personalidad': 'Perseverante, energético',
        'entrada': ["Has llegado a Ecuaria. Que no encuentres la solución todavía",
                    "no significa que no exista."],
        'nivel': ["¡Excelente combinación!", "Esa es la estructura que buscabas."],
        'tiempo_agotado': ["Casi. Prueba otro multiplicador k.",
                            "No necesitas ir más rápido. Necesitas comprender qué está fallando."],
    },
    'espacios': {
        'continente': 'Dimensia',
        'guardian': 'Nexo',
        'identidad': 'Violeta · geometría abstracta',
        'personalidad': 'Filosófico, misterioso',
        'entrada': ["No eres la cantidad de elementos que posees,",
                    "sino la relación entre ellos."],
        'nivel': [], 'tiempo_agotado': [],
    },
    'transformaciones': {
        'continente': 'Transformia',
        'guardian': 'Transforma',
        'identidad': 'Naranja · portales y espejos',
        'personalidad': 'Enigmática, profunda',
        'entrada': ["Cambiar no significa dejar de ser tú."],
        'nivel': [], 'tiempo_agotado': [],
    },
}


def continente(tema_id):
    return CONTINENTES.get(tema_id, CONTINENTES['matrices'])


def frase(tema_id, evento):
    """Devuelve una frase al azar del guardián para ese evento, o None si no hay."""
    banco = continente(tema_id).get(evento) or []
    return random.choice(banco) if banco else None
