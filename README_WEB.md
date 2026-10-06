# Candy Matrix en el navegador

El juego está hecho con pygame, que abre una ventana de escritorio y **no
escucha en ningún puerto**. Por eso la pestaña *Puertos* de VS Code no sirve
para compartirlo tal cual: solo reenvía programas que escuchan en un puerto TCP.

Para que se abra con un link hay que compilarlo a WebAssembly con
[pygbag](https://pygame-web.github.io/), que convierte el juego en una página
web. Eso es lo que hacen los scripts de esta carpeta.

## Compilar y probar en tu máquina

```bat
.venv\Scripts\pip install pygbag soundfile
.venv\Scripts\python convert_audio.py     ::  .wav  ->  .ogg  (solo la primera vez)
.venv\Scripts\python build_web.py         ::  compila a web/build/web/
.venv\Scripts\python serve_web.py         ::  sirve en http://127.0.0.1:8000
```

Para abrirlo desde el celular o la tablet en el mismo wifi:

```bat
.venv\Scripts\python serve_web.py --todas-las-interfaces
```

Imprime la dirección de red (algo como `http://10.9.207.199:8000`). Si no carga,
suele ser el Firewall de Windows pidiendo permiso para Python la primera vez.

La primera carga en el navegador tarda unos segundos: baja el intérprete de
Python compilado a WebAssembly (unos 10 MB, se queda en caché). El juego en sí
pesa unos 110 KB.

## Publicar un link permanente (gratis)

Lo que hay en `web/build/web/` son archivos estáticos: `index.html`,
`web.tar.gz`, `favicon.png`, `sw.js`. Cualquier hosting estático gratuito funciona, y así no
hace falta dejar la computadora prendida ni reenviar puertos.

### GitHub Pages — ya está publicado

**El juego está en vivo aquí:**

> ### https://johangarciafdl.github.io/CANDY_MATRIX/

Se sirve desde la rama `gh-pages`, que contiene **solo lo que genera
`build_web.py`**: `index.html`, `web.tar.gz`, `favicon.png`, `sw.js`, la fuente
del título y un `.nojekyll`. No se
edita a mano — se regenera. El código fuente vive en `master`.

#### Volver a publicar después de un cambio

```bat
.venv\Scripts\python deploy_web.py
```

Compila (con todas las verificaciones de `build_web.py`) y sube el resultado a
`gh-pages`. Trabaja en un `git worktree` temporal, así que tu carpeta nunca
cambia de rama. Hay que hacerlo tras cada cambio: la rama `gh-pages` guarda el
resultado, no el código, y un commit en `master` no cambia el sitio por sí solo.

GitHub tarda un minuto largo en servir la versión nueva. Si ves la anterior,
recarga forzando (Ctrl+F5, o en el celular borrando los datos del sitio).

## Por qué tarda en cargar, y qué se hizo

Medido en un navegador real (Chrome) con una conexión de ~100 KB/s:

| | Antes | Ahora |
|---|---|---|
| Primera visita | nunca terminaba | ~100–135 s (depende de la red) |
| Siguientes visitas | — | ~15–25 s |

**Lo que más pesa es Python, no el juego.** pygbag descarga de su CDN unos
10 MB comprimidos: el motor (`main.wasm`, 4,5 MB), la biblioteca estándar
(`main.data`, 4,4 MB) y pygame (1,5 MB). El juego en sí son ~210 KB. A esa
velocidad la primera visita no puede bajar de ~1,5 minutos; donde sí se gana es
en las siguientes.

**`sw.js` (service worker)** guarda todo eso en el dispositivo. El CDN de
pygbag solo deja cachearlo 10 minutos (`Cache-Control: max-age=600`), así que
sin él se volvía a pedir casi en cada visita. Las rutas del intérprete llevan
la versión (`/cdn/0.9.3/`, `pygame_ce-2.5.7…whl`), así que guardarlas para
siempre no arriesga quedarse con una copia vieja. Los archivos del juego, en
cambio, se piden siempre a la red primero: una publicación nueva se ve al
recargar. Además, pide pygame en cuanto empieza la descarga del motor, para
que baje mientras Python arranca y no después.

**`web_template.tmpl`** es la pantalla de carga. La de pygbag ocultaba la barra
de progreso y solo decía "Loading, please wait…", y su barra solo seguía uno de
los dos archivos grandes (que bajan en paralelo), así que marcaba 100 % con
medio minuto de descarga por delante. La nueva suma el progreso real de todos
(lo cuenta `sw.js`), dice en español en qué fase está y, si la conexión va
lenta, lo avisa. Al tocar la pantalla desbloquea el audio en ese mismo gesto:
pygbag lo reintentaba solo cada 2 s.

Lo que queda tras la descarga son ~15 s de **Python arrancando dentro del
navegador** (trabajo del procesador). Eso es del motor de pygbag y no se puede
acortar desde el juego.

### Probar en local: 127.0.0.1, no localhost

Si la dirección contiene `//localhost:`, pygbag cree que lo sirve su propio
servidor de pruebas y pide pygame a `localhost/cdn/…`: da 404 y el juego queda
en negro sin ningún error visible. `serve_web.py` se abre en
`http://127.0.0.1:8000`, que se comporta igual que GitHub Pages.

`serve_web.py` tampoco envía cabeceras COOP/COEP: GitHub Pages no las envía y
con `Cross-Origin-Embedder-Policy: require-corp` el juego ni arranca.

### itch.io — la alternativa más simple

Pensado para juegos y no requiere git. Compila con el archivo comprimido y
súbelo:

```bat
.venv\Scripts\python -m pygbag --archive --build web
```

En itch.io: *Create new project → Kind of project: HTML → Upload* el
`web.zip`, y marca **"This file will be played in the browser"**.

## PythonAnywhere no sirve para esto

PythonAnywhere ejecuta aplicaciones web WSGI (Django, Flask): no tiene pantalla
ni servidor gráfico, así que `pygame.display.set_mode()` falla ahí. Subir el
juego tal cual no funciona, y hacerlo funcionar significaría reescribirlo entero
como aplicación web. Para un juego de pygame el camino correcto es compilarlo a
WebAssembly, como hace `build_web.py`, y publicar el resultado en cualquier
hosting estático.

## Por qué el código es asíncrono

En el navegador el juego comparte el hilo con la página: si un bucle no devuelve
el control, la pestaña se congela y ni se puede cerrar. Por eso cada bucle de
renderizado cede el control una vez por fotograma:

```python
pygame.display.flip()
clock.tick(Config.FPS)
await asyncio.sleep(0)      # <- deja respirar al navegador
```

Eso obliga a que la función que contiene el bucle sea `async def`, y a que todas
las que la llaman usen `await`. En este proyecto son 13 funciones: las pantallas
(`mostrar_intro`, `pedir_nombre`, `mostrar_menu_inicio`, `mostrar_hub_temas`,
`mostrar_mapa_niveles`, `mostrar_zona_estudio`, `mostrar_boss`, `fade_in`), los
tres `jugar` de los minijuegos y los ayudantes que abren una pregunta
(`preguntar_para_habilidad`, `manejar_click_habilidad`).

En escritorio no cambia nada: `asyncio.run(main())` se comporta igual que el
código síncrono de antes, así que `python main.py` sigue funcionando como
siempre.

## Por qué los eventos pasan por `entrada.py`

En un celular SDL **no** entrega los toques como clics: manda `FINGERDOWN`,
`FINGERUP` y `FINGERMOTION`, con las coordenadas entre 0 y 1 en vez de píxeles.
Como el juego está escrito contra `MOUSEBUTTONDOWN` y `ev.pos`, sin traducirlos
no responde absolutamente nada en el celular: ni los botones, ni el teclado en
pantalla, ni el tablero.

`entrada.py` hace esa traducción en el único punto por donde entran los eventos,
así que el resto del código sigue hablando de clics:

```python
import entrada

for ev in entrada.obtener_eventos():     # en vez de pygame.event.get()
    ...
mouse_pos = entrada.posicion_puntero()   # en vez de pygame.mouse.get_pos()
```

`posicion_puntero()` hace falta porque `pygame.mouse.get_pos()` no sigue al
dedo: sin ella ningún botón se vería pulsado y el jugador no tendría señal de
estar tocando el sitio correcto.

## Al agregar una pantalla o un minijuego nuevo

1. Si tiene su propio bucle, hazla `async def`, pon `await asyncio.sleep(0)`
   dentro del bucle y `await` en quien la llame.
2. Lee los eventos con `entrada.obtener_eventos()`, nunca con
   `pygame.event.get()`.

`build_web.py` comprueba las dos cosas que puede comprobar: que no falte ningún
módulo y que nadie lea los eventos por su cuenta. Lo que **no** puede detectar
es un `await` que falta — eso compila igual y el juego se congela en el
navegador.

## Sonidos de la cinemática

Los efectos `assets/sounds/cine_*.ogg` (27 archivos, ~300 KB) se sintetizan con
código en `generar_sonidos.py`: sin licencias de terceros y cada uno hecho a la
medida de su momento (todos en re, para que combinen al solaparse). Para
ajustarlos, se edita ese archivo y se regeneran:

```bat
.venv\Scripts\pip install numpy soundfile
.venv\Scripts\python generar_sonidos.py
```

El juego no los decodifica al arrancar (costaría ~0,6 s en el PC, más en el
navegador): la cinemática los carga uno por fotograma durante su fundido inicial
en negro, en el orden en que suenan. Su volumen relativo está en
`sound_manager.py` (`VOLUMENES_CINE`).
