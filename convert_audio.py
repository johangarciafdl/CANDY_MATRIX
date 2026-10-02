# convert_audio.py
"""Convierte los sonidos de assets/sounds/ de .wav a .ogg (Ogg Vorbis).

Hace falta para la versión web: el mixer de SDL compilado a WebAssembly solo
reproduce Ogg Vorbis de forma fiable — los .wav o no suenan o salen cortados.
Además pesan unas diez veces más, y en el navegador el juego no arranca hasta
haber descargado todos los assets.

Se usa `soundfile` (libsndfile) en lugar de ffmpeg para no depender de un
binario externo que no viene con el entorno virtual.

Uso:
    .venv\\Scripts\\pip install soundfile
    .venv\\Scripts\\python convert_audio.py

Los .wav se conservan: sound_manager.py prefiere el .ogg y cae al .wav si no
existe, así que la versión de escritorio sigue funcionando igual.
"""
import glob
import os
import sys

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sounds")


def main():
    try:
        import soundfile as sf
    except ImportError:
        sys.exit("Falta soundfile. Instálalo con: .venv\\Scripts\\pip install soundfile")

    if "OGG" not in sf.available_formats():
        sys.exit("Esta instalación de libsndfile no sabe escribir Ogg Vorbis.")

    wavs = sorted(glob.glob(os.path.join(CARPETA, "*.wav")))
    if not wavs:
        sys.exit("No se encontraron .wav en %s" % CARPETA)

    total_wav = total_ogg = 0
    for wav in wavs:
        ogg = os.path.splitext(wav)[0] + ".ogg"
        datos, frecuencia = sf.read(wav)
        sf.write(ogg, datos, frecuencia, format="OGG", subtype="VORBIS")

        peso_wav, peso_ogg = os.path.getsize(wav), os.path.getsize(ogg)
        total_wav += peso_wav
        total_ogg += peso_ogg
        print("%-24s %7.1f KB -> %6.1f KB" % (
            os.path.basename(ogg), peso_wav / 1024, peso_ogg / 1024))

    print("-" * 46)
    print("%-24s %7.1f KB -> %6.1f KB" % ("TOTAL", total_wav / 1024, total_ogg / 1024))


if __name__ == "__main__":
    main()
