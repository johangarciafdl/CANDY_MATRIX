import pygame, sys
from config import Config
from matrix_logic import generar_tablero
from sound_manager import SoundManager
from learn_zone import mostrar_zona_estudio
from ui import mostrar_menu_inicio
from hub import mostrar_hub_temas
from intro import mostrar_intro
from login import pedir_nombre
from level_map import mostrar_mapa_niveles
import matrix_game
import vector_game
import system_game

# Inicialización
pygame.init()
ventana = pygame.display.set_mode((Config.ANCHO, Config.ALTO))
pygame.display.set_caption("Candy Matrix - Proyecto Álgebra Lineal")

sound = SoundManager(autoplay_music=False)

mostrar_intro(ventana, sound)
sound.iniciar_musica()
estudiante = pedir_nombre(ventana)

JUEGOS_POR_TEMA = {
    'matrices': matrix_game.jugar,
    'vectores': vector_game.jugar,
    'sistemas': system_game.jugar,
}

# -------------------- Bucle principal --------------------
# Cada jugar(...) corre sus propias partidas (incluidos los "Jugar de nuevo")
# hasta que el jugador pide el menú principal o cierra la ventana; por eso este
# bucle solo se repite para volver a mostrar el menú, el Hub de temas y el
# mapa de niveles.

tema_actual = 'matrices'

while True:
    inicio = mostrar_menu_inicio(ventana)
    if not inicio:
        break

    tema_elegido = mostrar_hub_temas(ventana, estudiante, tema_actual)
    if tema_elegido is None:
        continue  # volvió del Hub sin elegir: mostrar el menú principal de nuevo
    tema_actual = tema_elegido

    if inicio == "estudio":
        mostrar_zona_estudio(ventana, generar_tablero(), sound, tema_actual)

    nivel_elegido = mostrar_mapa_niveles(ventana, tema_actual, estudiante)
    if nivel_elegido is None:
        continue  # volvió del mapa de niveles sin elegir: al menú de nuevo

    jugar = JUEGOS_POR_TEMA[tema_actual]
    if jugar(ventana, sound, tema_actual, estudiante, nivel_inicial=nivel_elegido) == 'salir':
        break

pygame.quit()
sys.exit()
