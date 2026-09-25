# sound_manager.py
import os
from pygame import mixer

class SoundManager:
    def __init__(self, assets_base='assets/sounds'):
        try:
            mixer.init()
        except Exception:
            pass
        self.assets_base = assets_base
        self.sounds = {}
        self._load_sounds()
        self._setup_music()

    def _sound_path(self, name):
        return os.path.join(self.assets_base, name)

    def _load_sounds(self):
        mapping = {
            'explosion': 'pop.wav',
            'correct': 'levelup.wav',
            'error': 'error.wav',
            'levelup': 'levelup.wav',
        }
        for key, fname in mapping.items():
            path = self._sound_path(fname)
            if os.path.exists(path):
                try:
                    self.sounds[key] = mixer.Sound(path)
                except Exception as e:
                    print(f"Warning: no se pudo cargar {path}: {e}")

    def _setup_music(self):
        music_path = self._sound_path('background_music.wav')
        if os.path.exists(music_path):
            try:
                mixer.music.load(music_path)
                mixer.music.set_volume(0.2)
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
