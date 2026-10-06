// sw.js — guarda el intérprete de Python en el dispositivo y cuenta su descarga.
//
// pygbag descarga unos 9 MB (comprimidos) de Python para WebAssembly desde
// pygame-web.github.io, y ese servidor solo permite cachearlo 10 minutos
// (Cache-Control: max-age=600). Medido en un navegador real a ~100 KB/s: la
// primera visita tarda ~90 s y, con este service worker, la segunda ~18 s
// (lo que queda es Python arrancando dentro del navegador, no descargas).
//
// Reglas, a propósito distintas:
//  - Intérprete (rutas con versión: /cdn/0.9.3/, index-0.9.3-...): primero la
//    caché. No cambian dentro de una versión, así que no hay riesgo de quedarse
//    con una copia vieja; si pygbag cambia de versión, cambian las rutas.
//  - Terminal de pygbag (/cdn/vt/, sin versión): se sirve lo guardado y se
//    actualiza por detrás para la próxima visita.
//  - Archivos del juego (index.html, web.tar.gz...): primero la red, para que
//    cada publicación nueva se vea al recargar; lo guardado solo sin conexión.
//
// Además avisa a la página de cuántos bytes lleva cada descarga grande: la
// barra de progreso de pygbag solo sigue uno de los dos archivos grandes, que
// bajan en paralelo, y marcaba 100 % mientras el otro seguía bajando.

const CDN = "https://pygame-web.github.io/cdn/";
const VERSION = "0.9.3";
const CACHE_RUNTIME = "candy-runtime-pygbag-" + VERSION;
const CACHE_JUEGO = "candy-juego-1";

// pygame no viene dentro del motor: pygbag lo descarga como paquete (1,5 MB)
// cuando Python ya arrancó, al ejecutar los import del juego. Se pide por
// adelantado, en cuanto empieza la descarga del motor, para que baje mientras
// Python se inicia (~14 s de trabajo del procesador) y no después. El nombre
// lleva la versión, así que tampoco cambia nunca.
const PRECARGA = [CDN + "cp312/pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl"];
const enCurso = new Map();  // descargas por adelantado que aún no terminan

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (evento) => {
    evento.waitUntil((async () => {
        for (const nombre of await caches.keys()) {
            if (nombre !== CACHE_RUNTIME && nombre !== CACHE_JUEGO) await caches.delete(nombre);
        }
        // Controlar ya esta página, para que las descargas grandes que el
        // cargador pide justo después de arrancar se guarden en esta visita.
        await self.clients.claim();
    })());
});

self.addEventListener("fetch", (evento) => {
    const peticion = evento.request;
    if (peticion.method !== "GET" || peticion.headers.has("range")) return;
    const url = peticion.url;
    if (url.endsWith("/main.wasm")) evento.waitUntil(Promise.all(PRECARGA.map(precargar)));
    // Rutas que no cambian nunca: llevan la versión de pygbag en la carpeta
    // (/cdn/0.9.3/), en el nombre del índice, o en el nombre del paquete (.whl).
    if (url.startsWith(CDN + VERSION + "/") || url.startsWith(CDN + "index-" + VERSION) ||
        (url.startsWith(CDN) && url.split("#")[0].endsWith(".whl"))) {
        evento.respondWith(primeroCache(peticion));
    } else if (url.startsWith(CDN + "vt/")) {
        evento.respondWith(guardadoYActualizar(peticion));
    } else if (new URL(url).origin === self.location.origin) {
        evento.respondWith(primeroRed(peticion));
    }
});

function guardable(respuesta) {
    // Solo respuestas completas y legibles: una parcial (206) no se puede
    // guardar, y una "opaca" ocupa en la cuota mucho más de lo que pesa.
    return respuesta && respuesta.status === 200 && respuesta.type !== "opaque";
}

async function avisar(url, bytes, completo) {
    const clientes = await self.clients.matchAll({ includeUncontrolled: true });
    for (const cliente of clientes) cliente.postMessage({ tipo: "descarga", url, bytes, completo });
}

function contarDescarga(url, respuesta) {
    // Pasa el cuerpo por un contador que avisa cada 64 KB. Se quitan
    // Content-Length y Content-Encoding porque describen el cuerpo comprimido
    // y lo que sigue ya está descomprimido.
    if (!respuesta.body) return respuesta;
    let recibido = 0, ultimoAviso = 0;
    const contador = new TransformStream({
        transform(trozo, control) {
            recibido += trozo.byteLength;
            if (recibido - ultimoAviso >= 65536) {
                ultimoAviso = recibido;
                avisar(url, recibido, false);
            }
            control.enqueue(trozo);
        },
        flush() { avisar(url, recibido, true); },
    });
    const cabeceras = new Headers(respuesta.headers);
    cabeceras.delete("content-length");
    cabeceras.delete("content-encoding");
    return new Response(respuesta.body.pipeThrough(contador), {
        status: respuesta.status, statusText: respuesta.statusText, headers: cabeceras,
    });
}

function limpia(url) {
    return url.split("#")[0];  // pygbag añade "#" al final de algunas URL
}

async function precargar(url) {
    if (enCurso.has(url)) return;
    const cache = await caches.open(CACHE_RUNTIME);
    if (await cache.match(url)) {
        avisar(url, 0, true);
        return;
    }
    const tarea = (async () => {
        const respuesta = await fetch(new Request(url, { mode: "cors", credentials: "omit" }));
        if (guardable(respuesta)) await cache.put(url, contarDescarga(url, respuesta));
    })().catch(() => {}).finally(() => enCurso.delete(url));
    enCurso.set(url, tarea);
    return tarea;
}

async function primeroCache(peticion) {
    const url = limpia(peticion.url);
    const cache = await caches.open(CACHE_RUNTIME);
    let guardada = await cache.match(url);
    if (!guardada && enCurso.has(url)) {
        // Ya se está bajando por adelantado: esperar esa descarga en vez de
        // empezar otra igual.
        await enCurso.get(url);
        guardada = await cache.match(url);
    }
    if (guardada) {
        avisar(url, 0, true);  // ya está: la barra salta a completo
        return guardada;
    }
    // pygbag carga main.js con una etiqueta <script> (modo no-cors): la
    // respuesta llega "opaca" y no se puede leer, contar ni guardar con
    // seguridad, así que se volvía a descargar en cada visita. El servidor de
    // pygbag permite CORS (Access-Control-Allow-Origin: *), así que se pide en
    // modo CORS; una respuesta CORS sirve igual para una petición no-cors.
    const real = peticion.mode === "no-cors"
        ? new Request(url, { mode: "cors", credentials: "omit" })
        : peticion;
    const respuesta = await fetch(real);
    if (!guardable(respuesta)) return respuesta;
    const contada = contarDescarga(url, respuesta);
    cache.put(url, contada.clone()).catch(() => {});
    return contada;
}

async function guardadoYActualizar(peticion) {
    const cache = await caches.open(CACHE_RUNTIME);
    const guardada = await cache.match(peticion);
    const deRed = fetch(peticion).then((respuesta) => {
        if (guardable(respuesta)) cache.put(peticion, respuesta.clone()).catch(() => {});
        return respuesta;
    });
    if (guardada) {
        deRed.catch(() => {});
        return guardada;
    }
    return deRed;
}

async function primeroRed(peticion) {
    const cache = await caches.open(CACHE_JUEGO);
    try {
        const respuesta = await fetch(peticion);
        if (guardable(respuesta)) cache.put(peticion, respuesta.clone()).catch(() => {});
        return respuesta;
    } catch (error) {
        const guardada = await cache.match(peticion);
        if (guardada) return guardada;
        throw error;
    }
}
