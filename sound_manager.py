# sound_manager.py
import os
from pygame import mixer

# Volumen de cada efecto de la cinemática (generados por generar_sonidos.py).
# Los archivos están normalizados al mismo pico, pero no suenan igual de fuerte:
# aquí se equilibra la mezcla para que ningún momento tape al siguiente.
VOLUMENES_CINE = {
    'cine_ambiente': 0.55, 'cine_rafaga': 0.45, 'cine_acorde': 0.6,
    'cine_vacio': 0.8, 'cine_grieta': 0.5, 'cine_estallido': 0.9,
    'cine_chispa': 0.5, 'cine_calidez': 0.42, 'cine_subida': 0.4,
    'cine_titulo': 0.6,
}
VOLUMEN_POR_PREFIJO = {'cine_brillo': 0.32, 'cine_encaje': 0.28, 'cine_letra': 0.38}

class SoundManager:
    def __init__(self, assets_base='assets/sounds', autoplay_music=True):
        try:
            mixer.init()
            # 8 canales (los de pygame) no alcanzan: en la cinemática suenan a la
            # vez el ambiente, varios destellos y los clics de las fichas, y un
            # sonido nuevo cortaría a otro que aún no terminó.
            mixer.set_num_channels(32)
        except Exception:
            pass
        self.assets_base = assets_base
        self.sounds = {}
        self._load_sounds()
        self._preparar_musica()
        if autoplay_music:
            self.iniciar_musica()

    def _sound_path(self, name):
        """Devuelve la ruta del sonido prefiriendo .ogg sobre .wav.

        En el navegador (pygbag) el mixer de SDL solo reproduce Ogg Vorbis de
        forma fiable: .wav suele fallar o sonar cortado. En escritorio los dos
        funcionan, asi que se busca primero el .ogg y se usa el .wav como
        respaldo; de ese modo el mismo codigo sirve en ambas plataformas.
        """
        base, _ext = os.path.splitext(name)
        for candidato in (base + '.ogg', name):
            ruta = os.path.join(self.assets_base, candidato)
            if os.path.exists(ruta):
                return ruta
        return os.path.join(self.assets_base, name)

    def _load_sounds(self):
        mapping = {
            'explosion': 'pop.wav',
            'correct': 'levelup.wav',
            'error': 'error.wav',
            'levelup': 'levelup.wav',
            'chime': 'chime.wav',
            'shatter': 'shatter.wav',
        }
        for key, fname in mapping.items():
            path = self._sound_path(fname)
            if os.path.exists(path):
                try:
                    self.sounds[key] = mixer.Sound(path)
                except Exception as e:
                    print(f"Warning: no se pudo cargar {path}: {e}")

        # Efectos de la cinemática (cine_*.ogg): solo se anotan, no se
        # decodifican aquí. Decodificar los 27 cuesta ~0,6 s en el PC (unos
        # 10 ms por segundo de audio) y bastante más en el navegador, y eso se
        # sumaba a la espera de carga. La cinemática los carga uno por
        # fotograma, en el orden en que los necesita (ver cargar()).
        try:
            nombres = sorted(f for f in os.listdir(self.assets_base)
                             if f.startswith('cine_') and f.endswith('.ogg'))
        except OSError:
            nombres = []
        self._pendientes = {f[:-4]: os.path.join(self.assets_base, f) for f in nombres}

    def _preparar_musica(self):
        """Solo carga la música de fondo; iniciar_musica() decide cuándo
        arranca (durante el prólogo se prefiere silencio + efectos propios)."""
        music_path = self._sound_path('background_music.wav')
        self._musica_disponible = os.path.exists(music_path)
        if self._musica_disponible:
            try:
                mixer.music.load(music_path)
                mixer.music.set_volume(0.2)
            except Exception as e:
                print("Warning: no se pudo preparar la música:", e)
                self._musica_disponible = False

    def iniciar_musica(self):
        if self._musica_disponible:
            try:
                mixer.music.play(-1)
            except Exception as e:
                print("Warning: no se pudo reproducir la música:", e)

    def cargar(self, clave):
        """Decodifica un efecto pendiente (no hace nada si ya está cargado)."""
        ruta = self._pendientes.pop(clave, None)
        if ruta is None:
            return
        try:
            snd = mixer.Sound(ruta)
        except Exception as e:
            print(f"Warning: no se pudo cargar {ruta}: {e}")
            return
        volumen = VOLUMENES_CINE.get(clave)
        if volumen is None:
            volumen = next((v for pref, v in VOLUMEN_POR_PREFIJO.items()
                            if clave.startswith(pref)), 1.0)
        snd.set_volume(volumen)
        self.sounds[clave] = snd

    def pendientes(self):
        return list(self._pendientes)

    def play(self, name):
        if name in self._pendientes:
            self.cargar(name)  # red de seguridad: si aún no estaba, cargarlo ya
        snd = self.sounds.get(name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    def detener(self, name, fundido_ms=0):
        """Apaga un sonido largo (por ejemplo el ambiente) con un fundido."""
        snd = self.sounds.get(name)
        if snd:
            try:
                if fundido_ms > 0:
                    snd.fadeout(int(fundido_ms))
                else:
                    snd.stop()
            except Exception:
                pass

    def fundir_todo(self, fundido_ms):
        """Funde a silencio todos los efectos que estén sonando (no la música)."""
        try:
            mixer.fadeout(int(fundido_ms))
        except Exception:
            pass
