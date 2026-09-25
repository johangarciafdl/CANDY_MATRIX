# quiz_system.py
import random
from config import Config, COLOR_MAP

# Cada pregunta: (enunciado, es_verdadero, explicacion)
MATRICES_TF = [
    ("La suma de matrices A+B es conmutativa",
     True,
     "A+B = B+A porque se suman celda por celda, y la suma de números reales ya es conmutativa."),
    ("El producto de matrices AB = BA siempre",
     False,
     "El producto de matrices NO es conmutativo en general: AB y BA pueden tener incluso tamaños distintos."),
    ("Una matriz singular es no invertible",
     True,
     "Singular significa det(A) = 0, y una matriz solo tiene inversa cuando su determinante es distinto de cero."),
    ("El rango de una matriz es <= min(m,n)",
     True,
     "El rango cuenta filas/columnas linealmente independientes, y nunca puede superar el menor de sus dos tamaños."),
    ("Toda matriz es diagonalizable",
     False,
     "Solo son diagonalizables las matrices con suficientes autovectores linealmente independientes (no todas las matrices con autovalores repetidos lo son)."),
    ("tr(AB) = tr(BA) para toda matriz",
     True,
     "La traza es cíclica: tr(AB) = tr(BA), aunque AB y BA no sean iguales entre sí."),
    ("Los autovalores de una matriz siempre son números reales",
     False,
     "Una matriz real puede tener autovalores complejos, por ejemplo las matrices de rotación."),
    ("La traza es la suma de los autovalores",
     True,
     "tr(A) = suma de los elementos de la diagonal = suma de todos los autovalores (contados con su multiplicidad)."),
    ("Una matriz simétrica siempre es diagonalizable",
     True,
     "El teorema espectral garantiza que toda matriz simétrica real es diagonalizable mediante una base ortonormal de autovectores."),
    ("det(AB) = det(A) * det(B)",
     True,
     "El determinante del producto es el producto de los determinantes; por eso det(A) != 0 y det(B) != 0 implican det(AB) != 0."),
    ("La inversa de una matriz ortogonal es igual a su transpuesta",
     True,
     "Por definición, una matriz Q es ortogonal cuando Q^T Q = I, es decir Q^-1 = Q^T."),
    ("Una matriz triangular superior no tiene autovalores",
     False,
     "En una matriz triangular, los autovalores son exactamente los números de la diagonal principal."),
    ("El espacio nulo (kernel) de una matriz es un subespacio vectorial",
     True,
     "El conjunto de vectores x tales que Ax=0 siempre contiene al vector cero y es cerrado bajo suma y escalamiento."),
    ("Autovectores asociados a autovalores distintos son linealmente independientes",
     True,
     "Es un resultado clásico del álgebra lineal: autovalores distintos garantizan independencia lineal de sus autovectores."),
    ("Una matriz idempotente cumple A^2 = A",
     True,
     "Esa es justamente la definición de idempotente; geométricamente suele representar una proyección."),
    ("Una matriz identidad multiplicada por cualquier matriz A da como resultado A",
     True,
     "I actúa como el número 1 en la multiplicación de matrices: I*A = A*I = A."),
    ("Si dos filas de una matriz son iguales, su determinante es cero",
     True,
     "Filas repetidas hacen que las filas sean linealmente dependientes, y eso siempre anula el determinante."),
]

VECTORES_TF = [
    ("La suma de vectores u+v es conmutativa",
     True,
     "u+v = v+u porque se suman componente a componente, y la suma de números reales ya es conmutativa."),
    ("El producto punto de dos vectores da como resultado otro vector",
     False,
     "El producto punto u·v da como resultado un número (escalar), no un vector."),
    ("Si u·v = 0, los vectores u y v son ortogonales",
     True,
     "Un producto punto igual a cero es justamente la definición de vectores ortogonales (perpendiculares)."),
    ("La norma de un vector puede ser negativa",
     False,
     "La norma ||v|| es una raíz cuadrada de una suma de cuadrados, por lo que siempre es mayor o igual a cero."),
    ("Dos vectores solo se pueden sumar si tienen la misma dimensión",
     True,
     "La suma se hace componente a componente, así que ambos vectores deben tener el mismo número de componentes."),
    ("Un vector unitario es un vector cuya norma vale exactamente 1",
     True,
     "Por definición, normalizar un vector v es calcular v/||v|| para obtener un vector de norma 1 en la misma dirección."),
    ("El producto punto es conmutativo: u·v = v·u",
     True,
     "u·v = u1*v1+...+un*vn es una suma de productos de números reales, así que el orden no importa."),
    ("La norma al cuadrado de un vector es igual al producto punto del vector consigo mismo",
     True,
     "||v||^2 = v·v = v1^2 + v2^2 + ... + vn^2, por definición de norma y de producto punto."),
    ("El vector cero (0,0,...,0) es ortogonal a cualquier otro vector",
     True,
     "El producto punto de cualquier vector con el vector cero siempre da 0, así que cumple la condición de ortogonalidad."),
    ("Multiplicar un vector por un escalar negativo invierte su dirección",
     True,
     "Si k<0, el vector k*v apunta en sentido contrario a v, aunque conserve (o escale) su magnitud."),
    ("Restar dos vectores iguales siempre da el vector cero",
     True,
     "u - u = (u1-u1, u2-u2, ..., un-un) = (0,0,...,0) para cualquier vector u."),
]

SISTEMAS_TF = [
    ("Sumar un múltiplo de una ecuación a otra no cambia el conjunto solución del sistema",
     True,
     "Las operaciones elementales de fila (sumar un múltiplo de una fila a otra) preservan las soluciones del sistema; por eso son la base de la eliminación gaussiana."),
    ("Multiplicar una ecuación por 0 es una operación elemental válida",
     False,
     "Multiplicar por 0 convierte la ecuación en 0=0 y se pierde información: el escalar debe ser distinto de cero."),
    ("Un sistema de 2 ecuaciones con 2 incógnitas puede tener infinitas soluciones",
     True,
     "Si las dos ecuaciones describen la misma recta, cualquier punto de esa recta es solución del sistema."),
    ("Un sistema de 2 ecuaciones con 2 incógnitas puede no tener ninguna solución",
     True,
     "Si las rectas son paralelas y distintas, nunca se cruzan: el sistema es inconsistente."),
    ("Intercambiar el orden de dos ecuaciones cambia la solución del sistema",
     False,
     "El orden de las ecuaciones no importa: el conjunto solución es el mismo, solo cambia cómo se escribe el sistema."),
    ("El objetivo de la eliminación gaussiana es dejar ceros debajo de la diagonal principal",
     True,
     "Escalonar la matriz de coeficientes permite resolver el sistema por sustitución hacia atrás."),
    ("Si al combinar dos ecuaciones obtienes 0 = 5, el sistema no tiene solución",
     True,
     "Una fila del tipo 0 = c con c distinto de 0 es una contradicción: el sistema es inconsistente."),
    ("Si al combinar dos ecuaciones obtienes 0 = 0, el sistema siempre tiene solución única",
     False,
     "0=0 significa que esa ecuación era redundante; el sistema puede tener infinitas soluciones, no necesariamente una única."),
    ("La sustitución hacia atrás se usa después de escalonar el sistema",
     True,
     "Cuando una ecuación queda con una sola incógnita se despeja, y su valor se sustituye en las ecuaciones anteriores."),
    ("Un sistema de ecuaciones lineales se puede escribir en la forma Ax = b",
     True,
     "A es la matriz de coeficientes, x el vector de incógnitas y b el vector de términos independientes."),
]

asked_questions = {'matrices': set(), 'vectores': set(), 'sistemas': set()}


def make_mcq(question_text, correct_answer, distractors=None, explanation=""):
    if distractors is None:
        distractors = []
    # Sin deduplicar, una opción repetida deja dos botones válidos y solo uno
    # cuenta como acierto.
    options = [str(correct_answer)]
    for d in distractors:
        if str(d) not in options:
            options.append(str(d))
    random.shuffle(options)
    correct_idx = options.index(str(correct_answer))
    lines = wrap_text(question_text)
    return {
        'lines': lines,
        'options': options,
        'correct_idx': correct_idx,
        'explanation': explanation,
    }


def wrap_text(text, max_len=38):
    words = text.split()
    lines = []
    cur = words[0] if words else ''
    for w in words[1:]:
        if len(cur + ' ' + w) <= max_len:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def generate_matrix_mcq(tablero):
    """Genera una pregunta de opción múltiple usando los números reales del tablero actual."""
    typ = random.choice(['row_sum', 'col_sum', 'cell_val'])

    if typ == 'row_sum':
        r = random.randrange(Config.FILAS)
        valores = [v for v in tablero[r] if isinstance(v, int) and v >= 0]
        correct = sum(valores)
        distractors = list({correct + random.randint(-3, -1), correct + random.randint(1, 4)})
        q = f'¿Cuál es la suma de la fila {r + 1}?'
        exp = f"Fila {r + 1} = {valores}. Sumando sus valores: {' + '.join(map(str, valores))} = {correct}."
        return make_mcq(q, correct, distractors, exp)

    elif typ == 'col_sum':
        c = random.randrange(Config.COLUMNAS)
        colvals = [tablero[i][c] for i in range(Config.FILAS) if isinstance(tablero[i][c], int) and tablero[i][c] >= 0]
        correct = sum(colvals)
        distractors = list({correct + random.randint(-4, -1), correct + random.randint(1, 5)})
        q = f'¿Cuál es la suma de la columna {c + 1}?'
        exp = f"Columna {c + 1} = {colvals}. Sumando sus valores: {' + '.join(map(str, colvals))} = {correct}."
        return make_mcq(q, correct, distractors, exp)

    else:
        i = random.randrange(Config.FILAS)
        j = random.randrange(Config.COLUMNAS)
        val = tablero[i][j]
        correct = val if isinstance(val, int) and val >= 0 else 0
        # Los distractores se toman de los valores válidos distintos del correcto:
        # con correct=0, hacer correct-1 y recortar a 0 producía un "0" duplicado
        # y la opción correcta repetida se marcaba como incorrecta.
        distractors = random.sample([v for v in range(len(COLOR_MAP)) if v != correct], 2)
        q = f'¿Qué valor tiene la celda a_({i + 1},{j + 1})?'
        exp = f"En notación matricial, a_({i + 1},{j + 1}) es la fila {i + 1}, columna {j + 1} del tablero: vale {correct}."
        return make_mcq(q, correct, distractors, exp)


def concept_extra_question():
    """Preguntas conceptuales adicionales con explicación, fuera de la lista de V/F."""
    extra = [
        {
            'lines': wrap_text('¿Qué representa la traza de una matriz?'),
            'options': ['Suma de la diagonal principal', 'Producto de todas las filas', 'Número de columnas'],
            'correct_idx': 0,
            'explanation': "La traza tr(A) se define como la suma de los elementos de la diagonal principal (a11+a22+...+ann)."
        },
        {
            'lines': wrap_text('¿Cuándo una matriz cuadrada tiene inversa?'),
            'options': ['Cuando det(A) es distinto de 0', 'Cuando todos sus valores son positivos', 'Cuando es simétrica'],
            'correct_idx': 0,
            'explanation': "Una matriz cuadrada A es invertible si y solo si det(A) != 0; si det(A)=0 se dice que A es singular."
        },
        {
            'lines': wrap_text('¿Qué operación NO cambia el rango de una matriz?'),
            'options': ['Intercambiar dos filas', 'Borrar una fila completa', 'Eliminar una columna al azar'],
            'correct_idx': 0,
            'explanation': "Las operaciones elementales de fila (intercambiar, escalar, sumar un múltiplo de otra fila) preservan el rango; borrar filas o columnas sí puede cambiarlo."
        },
        {
            'lines': wrap_text('En un sistema Ax=b, ¿qué significa que la matriz A sea invertible?'),
            'options': ['El sistema tiene solución única', 'El sistema no tiene solución', 'El sistema tiene infinitas soluciones'],
            'correct_idx': 0,
            'explanation': "Si A es invertible, la única solución es x = A^-1 b: existe y es única."
        },
    ]
    return random.choice(extra)


def _filas_como_vectores(tablero, n=2):
    """Toma n filas distintas del tablero y las trata como vectores enteros."""
    indices = random.sample(range(Config.FILAS), min(n, Config.FILAS))
    vectores = []
    for i in indices:
        vectores.append([v if isinstance(v, int) and v >= 0 else 0 for v in tablero[i]])
    return indices, vectores


def generate_vector_mcq(tablero):
    """Genera una pregunta de opción múltiple tratando dos filas del tablero como vectores."""
    typ = random.choice(['suma_componente', 'producto_punto', 'norma_cuadrado'])
    (i1, i2), (u, v) = _filas_como_vectores(tablero, 2)

    if typ == 'suma_componente':
        k = random.randrange(len(u))
        correct = u[k] + v[k]
        distractors = list({correct + random.randint(-3, -1), correct + random.randint(1, 4)})
        q = f'u = fila {i1 + 1}, v = fila {i2 + 1}. ¿Cuál es la componente {k + 1} de u+v?'
        exp = f"(u+v)_{k + 1} = u_{k + 1} + v_{k + 1} = {u[k]} + {v[k]} = {correct}."
        return make_mcq(q, correct, distractors, exp)

    elif typ == 'producto_punto':
        correct = sum(a * b for a, b in zip(u, v))
        distractors = list({correct + random.randint(-6, -1), correct + random.randint(1, 7)})
        q = f'u = fila {i1 + 1}, v = fila {i2 + 1}. ¿Cuánto vale el producto punto u·v?'
        terminos = ' + '.join(f"{a}*{b}" for a, b in zip(u, v))
        exp = f"u·v = {terminos} = {correct}."
        return make_mcq(q, correct, distractors, exp)

    else:  # norma_cuadrado
        correct = sum(a * a for a in u)
        distractors = list({max(0, correct + random.randint(-5, -1)), correct + random.randint(1, 6)})
        q = f'u = fila {i1 + 1}. ¿Cuánto vale la norma al cuadrado ||u||^2?'
        terminos = ' + '.join(f"{a}^2" for a in u)
        exp = f"||u||^2 = u·u = {terminos} = {correct}."
        return make_mcq(q, correct, distractors, exp)


def concept_extra_question_vectores():
    """Preguntas conceptuales adicionales sobre vectores, fuera de la lista de V/F."""
    extra = [
        {
            'lines': wrap_text('¿Qué representa la norma ||v|| de un vector?'),
            'options': ['Su longitud (magnitud)', 'La cantidad de componentes', 'El producto de sus componentes'],
            'correct_idx': 0,
            'explanation': "||v|| = raíz(v1^2+v2^2+...+vn^2) mide la longitud del vector, no su dimensión ni un producto."
        },
        {
            'lines': wrap_text('¿Cuándo dos vectores son ortogonales?'),
            'options': ['Cuando su producto punto es 0', 'Cuando tienen la misma norma', 'Cuando todas sus componentes son iguales'],
            'correct_idx': 0,
            'explanation': "Dos vectores u, v son ortogonales (perpendiculares) exactamente cuando u·v = 0."
        },
        {
            'lines': wrap_text('¿Qué hace falta para normalizar un vector v (norma != 0)?'),
            'options': ['Dividir v entre ||v||', 'Multiplicar v por su norma', 'Sumarle el vector cero'],
            'correct_idx': 0,
            'explanation': "Normalizar es calcular v/||v||: el resultado apunta en la misma dirección pero con norma 1."
        },
        {
            'lines': wrap_text('¿Qué condición deben cumplir u y v para poder sumarlos?'),
            'options': ['Tener la misma dimensión', 'Tener la misma norma', 'Ser ortogonales entre sí'],
            'correct_idx': 0,
            'explanation': "La suma es componente a componente, así que u y v deben tener exactamente el mismo número de componentes."
        },
    ]
    return random.choice(extra)


def generar_sistema_2x2(rango=4):
    """Genera un sistema 2x2 con solución entera garantizada Y con al menos un
    entero k pequeño (|k|<=4) tal que Fila2 + k·Fila1 elimina una incógnita:
    sin esta garantía, el minijuego de eliminación podría generar sistemas
    imposibles de resolver combinando con un k entero."""
    x0 = random.randint(-rango, rango)
    y0 = random.randint(-rango, rango)
    a1 = random.choice([v for v in range(-rango, rango + 1) if v != 0])
    b1 = random.choice([v for v in range(-rango, rango + 1) if v != 0])
    c1 = a1 * x0 + b1 * y0

    m = random.choice([v for v in range(-4, 5) if v != 0])
    if random.random() < 0.5:
        a2 = m * a1
        while True:
            b2 = random.choice([v for v in range(-rango, rango + 1) if v != 0])
            if b2 - m * b1 != 0:  # evita una fila degenerada (0=0) al combinar con k=-m
                break
    else:
        b2 = m * b1
        while True:
            a2 = random.choice([v for v in range(-rango, rango + 1) if v != 0])
            if a2 - m * a1 != 0:
                break
    c2 = a2 * x0 + b2 * y0
    return (a1, b1, c1), (a2, b2, c2), (x0, y0)


def _formatea_ecuacion(fila):
    a, b, c = fila
    return f"{a}x + {b}y = {c}".replace("+ -", "- ")


def generate_system_mcq(tablero=None):
    """Genera una pregunta de opción múltiple sobre la solución de un sistema 2x2."""
    fila1, fila2, (x0, y0) = generar_sistema_2x2(rango=random.randint(2, 5))
    variable, correct = random.choice([('x', x0), ('y', y0)])
    distractors = list({correct + random.randint(-3, -1), correct + random.randint(1, 4)})
    q = (f'Sistema:  {_formatea_ecuacion(fila1)}   y   {_formatea_ecuacion(fila2)}.  '
         f'¿Cuánto vale {variable}?')
    exp = f"Resolviendo el sistema, la solución es x={x0}, y={y0}, así que {variable}={correct}."
    return make_mcq(q, correct, distractors, exp)


def concept_extra_question_sistemas():
    """Preguntas conceptuales adicionales sobre sistemas de ecuaciones."""
    extra = [
        {
            'lines': wrap_text('¿Qué representa la matriz aumentada [A|b] de un sistema Ax=b?'),
            'options': ['Los coeficientes A junto con los términos independientes b', 'Solo los coeficientes de x', 'La matriz inversa de A'],
            'correct_idx': 0,
            'explanation': "La matriz aumentada junta la matriz de coeficientes A y el vector b en una sola tabla para escalonar el sistema completo a la vez."
        },
        {
            'lines': wrap_text('¿Cuándo tiene solución única un sistema cuadrado Ax=b?'),
            'options': ['Cuando A es invertible (det(A) != 0)', 'Cuando todos los coeficientes son positivos', 'Cuando b es el vector cero'],
            'correct_idx': 0,
            'explanation': "Si A es invertible, la única solución es x = A^-1 b: existe y es única. Si det(A)=0, el sistema no tiene solución única."
        },
        {
            'lines': wrap_text('¿Qué operación NO es una operación elemental de fila válida?'),
            'options': ['Multiplicar una fila por 0', 'Sumar un múltiplo de una fila a otra', 'Intercambiar dos filas'],
            'correct_idx': 0,
            'explanation': "Multiplicar por 0 destruye información de esa ecuación; el escalar de una operación elemental debe ser distinto de cero."
        },
        {
            'lines': wrap_text('Si al escalonar obtienes la fila 0 = 0, ¿qué significa?'),
            'options': ['Que esa ecuación era combinación lineal de las otras', 'Que el sistema no tiene solución', 'Que hubo un error de cálculo'],
            'correct_idx': 0,
            'explanation': "0=0 indica que esa ecuación era redundante (dependiente de las demás): el sistema puede tener infinitas soluciones."
        },
    ]
    return random.choice(extra)


def _pick_matrix_question(tablero):
    pick = random.random()
    if pick < 0.4:
        vistas = asked_questions['matrices']
        available = [i for i in range(len(MATRICES_TF)) if i not in vistas]
        if not available:
            vistas.clear()
            available = list(range(len(MATRICES_TF)))
        idx = random.choice(available)
        vistas.add(idx)
        pregunta, respuesta, explicacion = MATRICES_TF[idx]
        return {
            'lines': wrap_text(pregunta),
            'options': ['Verdadero', 'Falso'],
            'correct_idx': 0 if respuesta else 1,
            'explanation': explicacion,
        }
    elif pick < 0.8:
        return generate_matrix_mcq(tablero)
    else:
        return concept_extra_question()


def _pick_vector_question(tablero):
    pick = random.random()
    if pick < 0.4:
        vistas = asked_questions['vectores']
        available = [i for i in range(len(VECTORES_TF)) if i not in vistas]
        if not available:
            vistas.clear()
            available = list(range(len(VECTORES_TF)))
        idx = random.choice(available)
        vistas.add(idx)
        pregunta, respuesta, explicacion = VECTORES_TF[idx]
        return {
            'lines': wrap_text(pregunta),
            'options': ['Verdadero', 'Falso'],
            'correct_idx': 0 if respuesta else 1,
            'explanation': explicacion,
        }
    elif pick < 0.8:
        return generate_vector_mcq(tablero)
    else:
        return concept_extra_question_vectores()


def _pick_system_question(tablero):
    pick = random.random()
    if pick < 0.4:
        vistas = asked_questions['sistemas']
        available = [i for i in range(len(SISTEMAS_TF)) if i not in vistas]
        if not available:
            vistas.clear()
            available = list(range(len(SISTEMAS_TF)))
        idx = random.choice(available)
        vistas.add(idx)
        pregunta, respuesta, explicacion = SISTEMAS_TF[idx]
        return {
            'lines': wrap_text(pregunta),
            'options': ['Verdadero', 'Falso'],
            'correct_idx': 0 if respuesta else 1,
            'explanation': explicacion,
        }
    elif pick < 0.8:
        return generate_system_mcq(tablero)
    else:
        return concept_extra_question_sistemas()


def pick_question(tablero, tema_id='matrices'):
    """Elige una pregunta variando entre banco V/F, preguntas del tablero/tema y
    conceptuales, usando el banco correspondiente al tema activo."""
    if tema_id == 'vectores':
        return _pick_vector_question(tablero)
    if tema_id == 'sistemas':
        return _pick_system_question(tablero)
    return _pick_matrix_question(tablero)
