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
.venv\Scripts\python serve_web.py         ::  sirve en http://localhost:8000
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
`web.apk`, `favicon.png`. Cualquier hosting estático gratuito funciona, y así no
hace falta dejar la computadora prendida ni reenviar puertos.

### GitHub Pages — ya está publicado

**El juego está en vivo aquí:**

> ### https://johangarciafdl.github.io/CANDY_MATRIX/

Se sirve desde la rama `gh-pages`, que contiene **solo lo que genera
`build_web.py`**: `index.html`, `web.apk`, `favicon.png` y un `.nojekyll`. No se
edita a mano — se regenera. El código fuente vive en `master`.

#### Volver a publicar después de un cambio

Siempre hay que recompilar: la rama `gh-pages` guarda el resultado, no el
código, así que un cambio en `master` no se refleja solo.

```bash
.venv\Scripts\python build_web.py          # 1. recompilar

git worktree add --detach .tmp-deploy      # 2. copia de trabajo aparte,
cd .tmp-deploy                             #    para no tocar tu carpeta
git checkout gh-pages
cp ../web/build/web/index.html ../web/build/web/web.apk ../web/build/web/favicon.png .
git add -A
git commit -m "Actualizar version web"
git push origin gh-pages

cd ..                                      # 3. limpiar
git worktree remove .tmp-deploy
```

GitHub tarda un minuto largo en servir la versión nueva. Si ves la anterior,
recarga forzando (Ctrl+F5, o en el celular borrando los datos del sitio).

#### Una limitación que conviene conocer

GitHub Pages no permite configurar cabeceras HTTP, así que no envía
`Cross-Origin-Embedder-Policy`. pygbag funciona sin ella (va en modo de un solo
hilo, sin `SharedArrayBuffer`), que es como corre este juego. Pero si algún día
se añade algo que necesite hilos, Pages dejará de servir y habrá que mover el
despliegue a itch.io, que sí tiene esa opción. El servidor local
(`serve_web.py`) sí manda esas cabeceras, así que puede funcionar algo en local
que falle en Pages: ante una diferencia rara entre los dos, sospecha de esto.

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
