import pygame
import numpy as np

class SoundManager:
    """
    Procedural sound manager for 2048 using synthesized waveforms.
    Generates chimes, slides, and celebration sounds without external audio assets.
    """
    def __init__(self):
        self.enabled = False
        self.muted = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
            self.sample_rate = 44100
            self._precompute_sounds()
        except Exception as e:
            # Audio device unavailable or disabled
            self.enabled = False

    def _make_sound(self, wave):
        audio = np.int16(np.clip(wave, -1.0, 1.0) * 32767)
        stereo = np.column_stack((audio, audio))
        return pygame.sndarray.make_sound(stereo)

    def _precompute_sounds(self):
        sr = self.sample_rate

        # 1. Slide Sound (Soft swoosh)
        dur = 0.05
        t = np.linspace(0, dur, int(sr * dur), False)
        noise = (np.random.rand(len(t)) * 2 - 1) * 0.05
        env = np.sin(np.pi * t / dur)
        self.slide_sound = self._make_sound(noise * env)

        # 2. Merge Chimes for each rank (4 up to 65536)
        self.merge_sounds = {}
        for rank in range(2, 17):
            val = 1 << rank
            dur = 0.12
            t = np.linspace(0, dur, int(sr * dur), False)
            freq = 340 + rank * 55
            env = np.exp(-18 * t)
            wave = 0.25 * (
                np.sin(2 * np.pi * freq * t) +
                0.3 * np.sin(2 * np.pi * freq * 2 * t)
            ) * env
            self.merge_sounds[val] = self._make_sound(wave)

        # 3. Milestone Celebration Sound (Arpeggio)
        dur = 0.4
        t = np.linspace(0, dur, int(sr * dur), False)
        wave = np.zeros_like(t)
        notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
        note_dur = dur / len(notes)
        for i, freq in enumerate(notes):
            t_start = i * note_dur
            mask = (t >= t_start) & (t < t_start + note_dur)
            t_rel = t[mask] - t_start
            wave[mask] = 0.3 * np.sin(2 * np.pi * freq * t_rel) * np.exp(-12 * t_rel)
        self.milestone_sound = self._make_sound(wave)

        # 4. Game Over Sound (Descending tones)
        dur = 0.45
        t = np.linspace(0, dur, int(sr * dur), False)
        wave = np.zeros_like(t)
        notes = [440, 370, 311, 261]
        note_dur = dur / len(notes)
        for i, freq in enumerate(notes):
            t_start = i * note_dur
            mask = (t >= t_start) & (t < t_start + note_dur)
            t_rel = t[mask] - t_start
            wave[mask] = 0.25 * np.sin(2 * np.pi * freq * t_rel) * np.exp(-10 * t_rel)
        self.game_over_sound = self._make_sound(wave)

    def play_slide(self):
        if self.enabled and not self.muted:
            try:
                self.slide_sound.play()
            except Exception:
                pass

    def play_merge(self, tile_value):
        if self.enabled and not self.muted:
            try:
                snd = self.merge_sounds.get(tile_value, self.merge_sounds[4])
                snd.play()
            except Exception:
                pass

    def play_milestone(self):
        if self.enabled and not self.muted:
            try:
                self.milestone_sound.play()
            except Exception:
                pass

    def play_game_over(self):
        if self.enabled and not self.muted:
            try:
                self.game_over_sound.play()
            except Exception:
                pass

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted
