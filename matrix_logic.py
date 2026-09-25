# matrix_logic.py
import random
from config import Config, COLOR_MAP

def _forma_linea(tablero, i, j):
    """True si el valor en (i,j) completa una línea de 3 con lo ya colocado."""
    v = tablero[i][j]
    if j >= 2 and tablero[i][j - 1] == v and tablero[i][j - 2] == v:
        return True
    if i >= 2 and tablero[i - 1][j] == v and tablero[i - 2][j] == v:
        return True
    return False


def generar_tablero():
    """Genera un tablero sin combinaciones ya hechas, como en Candy Crush:
    el jugador debe crearlas, no encontrarlas regaladas."""
    tablero = [[None] * Config.COLUMNAS for _ in range(Config.FILAS)]
    for i in range(Config.FILAS):
        for j in range(Config.COLUMNAS):
            opciones = list(range(len(COLOR_MAP)))
            random.shuffle(opciones)
            for valor in opciones:
                tablero[i][j] = valor
                if not _forma_linea(tablero, i, j):
                    break
    return tablero

def son_adyacentes(p1, p2):
    (r1, c1), (r2, c2) = p1, p2
    return abs(r1 - r2) + abs(c1 - c2) == 1

def intercambiar(tablero, p1, p2, matrix_history=None, game_events=None):
    r1, c1 = p1
    r2, c2 = p2
    # guardar estado en historial si se pasa
    if matrix_history is not None:
        current_matrix = [[tablero[i][j] for j in range(Config.COLUMNAS)] for i in range(Config.FILAS)]
        matrix_history.append(current_matrix)
        if game_events is not None:
            game_events.append(f"Intercambio ({r1},{c1}) con ({r2},{c2})")
    tablero[r1][c1], tablero[r2][c2] = tablero[r2][c2], tablero[r1][c1]
    return tablero

def buscar_combinaciones(tablero):
    remove = set()
    # horizontales
    for i in range(Config.FILAS):
        run_color = tablero[i][0]
        run_start = 0
        for j in range(1, Config.COLUMNAS + 1):
            color = tablero[i][j] if j < Config.COLUMNAS else None
            if color == run_color:
                continue
            else:
                length = j - run_start
                if run_color is not None and length >= 3:
                    for k in range(run_start, j):
                        remove.add((i, k))
                if j < Config.COLUMNAS:
                    run_color = tablero[i][j]
                    run_start = j
    # verticales
    for j in range(Config.COLUMNAS):
        run_color = tablero[0][j]
        run_start = 0
        for i in range(1, Config.FILAS + 1):
            color = tablero[i][j] if i < Config.FILAS else None
            if color == run_color:
                continue
            else:
                length = i - run_start
                if run_color is not None and length >= 3:
                    for k in range(run_start, i):
                        remove.add((k, j))
                if i < Config.FILAS:
                    run_color = tablero[i][j]
                    run_start = i
    return remove

def aplicar_gravedad(tablero):
    """Hace caer las piezas para tapar los huecos (None) y rellena por arriba con
    piezas nuevas. Devuelve una matriz con cuántas celdas cayó cada pieza, que es
    lo que la animación usa para dibujar el desplazamiento."""
    caidas = [[0] * Config.COLUMNAS for _ in range(Config.FILAS)]
    for j in range(Config.COLUMNAS):
        existentes = [(i, tablero[i][j]) for i in range(Config.FILAS) if tablero[i][j] is not None]
        faltantes = Config.FILAS - len(existentes)

        for idx, (fila_original, valor) in enumerate(existentes):
            fila_nueva = faltantes + idx
            tablero[fila_nueva][j] = valor
            caidas[fila_nueva][j] = fila_nueva - fila_original

        # Las piezas nuevas entran juntas desde arriba de la pantalla.
        for idx in range(faltantes):
            tablero[idx][j] = random.randrange(len(COLOR_MAP))
            caidas[idx][j] = faltantes

    return caidas

def sum_matrix(tablero):
    s=0
    for i in range(Config.FILAS):
        for j in range(Config.COLUMNAS):
            v = tablero[i][j]
            if isinstance(v,int) and v>=0:
                s+=v
    return s

def matrix_stats(tablero):
    vals=[]
    for i in range(Config.FILAS):
        for j in range(Config.COLUMNAS):
            v=tablero[i][j]
            if isinstance(v,int) and v>=0:
                vals.append(v)
    if not vals:
        return {'sum':0,'min':0,'max':0,'mean':0}
    return {'sum':sum(vals),'min':min(vals),'max':max(vals),'mean':sum(vals)/len(vals)}
