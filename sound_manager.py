# sound_manager.py
import os
from pygame import mixer

class SoundManager:
    def __init__(self, assets_base='assets/sounds', autoplay_music=True):
        try:
            mixer.init()
        except Exception:
            pass
        self.assets_base = assets_base
        self.sounds = {}
        self._load_sounds()
        self._preparar_musica()
        if autoplay_music:
            self.iniciar_musica()

    def _sound_path(self, name):
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

    def play(self, name):
        snd = self.sounds.get(name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass
