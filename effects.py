# effects.py
"""Sistema de partículas ligero y compartido, para subir la calidad de
animación (GDD: "Acierto: pop + partículas + rebote", "Nivel: confeti
geométrico") sin añadir dependencias nuevas. Cada minijuego del Hub llama
spawn_burst/spawn_confetti en sus momentos de éxito y update_and_draw en su
bucle de dibujo; las partículas viven en un estado interno de este módulo, así
que no hay que guardar nada en el estado de cada partida."""
import math
import random
import pygame

_particulas = []


def spawn_burst(x, y, color, cantidad=14, velocidad=220, vida=0.55):
    """Estallido radial de partículas, para un acierto/combo."""
    for _ in range(cantidad):
        ang = random.uniform(0, 2 * math.pi)
        vel = random.uniform(velocidad * 0.35, velocidad)
        _particulas.append({
            'x': x, 'y': y,
            'vx': math.cos(ang) * vel, 'vy': math.sin(ang) * vel,
            'vida': vida, 'edad': 0.0,
            'color': color, 'radio': random.uniform(2.5, 5.5),
            'gravedad': 260,
        })


def spawn_confetti(rect, cantidad=36, colores=None):
    """Lluvia de confeti geométrico para el cierre de nivel."""
    colores = colores or [(233, 90, 64), (60, 140, 200), (247, 203, 60),
                          (124, 190, 60), (155, 89, 182), (247, 147, 40)]
    for _ in range(cantidad):
        _particulas.append({
            'x': random.uniform(rect.x, rect.right), 'y': rect.y - random.uniform(0, 120),
            'vx': random.uniform(-40, 40), 'vy': random.uniform(60, 160),
            'vida': random.uniform(1.4, 2.2), 'edad': 0.0,
            'color': random.choice(colores), 'radio': random.uniform(3, 6),
            'gravedad': 140, 'giro': random.uniform(0, math.tau), 'vel_giro': random.uniform(-6, 6),
        })


def limpiar():
    _particulas.clear()


def update_and_draw(surface, dt):
    vivas = []
    for p in _particulas:
        p['edad'] += dt
        if p['edad'] >= p['vida']:
            continue
        p['vx'] *= 0.98
        p['vy'] += p['gravedad'] * dt
        p['x'] += p['vx'] * dt
        p['y'] += p['vy'] * dt
        t = p['edad'] / p['vida']
        alpha = max(0, int(255 * (1 - t)))
        radio = max(1, p['radio'] * (1 - 0.3 * t))

        capa = pygame.Surface((int(radio * 2) + 2, int(radio * 2) + 2), pygame.SRCALPHA)
        color = (*p['color'], alpha)
        if 'giro' in p:
            p['giro'] += p['vel_giro'] * dt
            rect = pygame.Rect(0, 0, radio * 1.6, radio * 1.6)
            rect.center = (capa.get_width() // 2, capa.get_height() // 2)
            forma = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(forma, color, forma.get_rect())
            forma = pygame.transform.rotate(forma, math.degrees(p['giro']))
            capa.blit(forma, forma.get_rect(center=(capa.get_width() // 2, capa.get_height() // 2)))
        else:
            pygame.draw.circle(capa, color, (capa.get_width() // 2, capa.get_height() // 2), int(radio))
        surface.blit(capa, (int(p['x'] - radio), int(p['y'] - radio)))
        vivas.append(p)
    _particulas[:] = vivas
