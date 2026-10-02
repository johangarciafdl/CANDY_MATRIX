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

### GitHub Pages — recomendado

Es gratis, el link es permanente y ya tienes el repositorio.

1. Compila: `.venv\Scripts\python build_web.py`
2. Crea una rama solo para la web y copia ahí el contenido de `web/build/web/`:

   ```bash
   git checkout --orphan gh-pages
   git rm -rf .
   cp -r web/build/web/* .
   git add index.html web.apk favicon.png
   git commit -m "Publicar version web"
   git push origin gh-pages
   ```

3. En GitHub: *Settings → Pages → Source: branch `gh-pages`, carpeta `/`*.
4. El link queda en `https://<tu-usuario>.github.io/<repositorio>/`.

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

**Al agregar un minijuego o una pantalla nueva**, si tiene su propio bucle:
hazla `async def`, pon `await asyncio.sleep(0)` dentro del bucle y `await` en
quien la llame. `build_web.py` avisa si olvidas incluir un módulo, pero un
`await` que falta no da error al compilar — el juego simplemente se congela en
el navegador.
