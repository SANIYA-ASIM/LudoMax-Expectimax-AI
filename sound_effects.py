"""
sound_effects.py — Procedural Sound System for LudoMax
======================================================
Synthesizes clean, pleasant sound effects directly in memory using PCM audio,
requiring zero external asset files. Supports full muting and graceful fallback.
"""
import math
import struct
from typing import Dict, Optional
import pygame


class SoundManager:
    """Manages audio effects, procedural synthesis, and mute toggle."""

    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        self.muted: bool = False
        self.available: bool = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1, buffer=512)
            self.available = True
            self._generate_sounds()
        except Exception:
            self.available = False

    def toggle_mute(self) -> bool:
        """Toggle mute state and return new state."""
        self.muted = not self.muted
        return self.muted

    def set_muted(self, muted: bool):
        self.muted = muted

    def play(self, sound_name: str):
        """Play sound effect by name if unmuted and available."""
        if self.muted or not self.available:
            return
        snd = self.sounds.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────────
    # Procedural Waveform Synthesis
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_pcm(self, generator, duration: float) -> bytes:
        """Generate 16-bit mono signed PCM bytes."""
        total_samples = int(self.sample_rate * duration)
        buf = bytearray()
        for i in range(total_samples):
            t = i / self.sample_rate
            sample_val = generator(t, duration)
            sample_val = max(-1.0, min(1.0, sample_val))
            int_val = int(sample_val * 32767)
            buf.extend(struct.pack('<h', int_val))
        return bytes(buf)

    def _generate_sounds(self):
        """Pre-compute all procedural audio waveforms."""
        # 1. Button click: short crisp 12ms pop
        def gen_click(t, d):
            env = math.exp(-t * 250)
            return math.sin(2 * math.pi * 750 * t) * env * 0.45

        # 2. Dice roll / tumble click
        def gen_dice(t, d):
            # multi-tap rattle
            t_rem = t % 0.05
            env = math.exp(-t_rem * 180) * (1 - t / d)
            freq = 420 + 200 * math.sin(t * 40)
            return math.sin(2 * math.pi * freq * t) * env * 0.5

        # 3. Piece move: soft wooden drop
        def gen_move(t, d):
            env = math.exp(-t * 25)
            freq = 320 - 100 * (t / d)
            return (math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * freq * 2 * t)) * env * 0.55

        # 4. Piece capture: exciting ascending double-chime
        def gen_capture(t, d):
            if t < 0.12:
                freq = 523.25  # C5
                env = math.exp(-t * 12)
            else:
                t2 = t - 0.12
                freq = 783.99  # G5
                env = math.exp(-t2 * 10)
            return math.sin(2 * math.pi * freq * t) * env * 0.65

        # 5. Extra turn chime: pleasant bright sparkle
        def gen_extra_turn(t, d):
            f = 659.25 if t < 0.1 else 987.77  # E5 -> B5
            env = math.exp(-(t % 0.1) * 15) * (1 - t / d * 0.5)
            return math.sin(2 * math.pi * f * t) * env * 0.6

        # 6. Piece home goal: melodic celebratory chime
        def gen_home(t, d):
            f1, f2, f3 = 523.25, 659.25, 783.99  # C - E - G chord
            env = math.exp(-t * 5)
            return (math.sin(2 * math.pi * f1 * t) * 0.4 +
                    math.sin(2 * math.pi * f2 * t) * 0.35 +
                    math.sin(2 * math.pi * f3 * t) * 0.35) * env * 0.7

        # 7. Victory fanfare
        def gen_victory(t, d):
            notes = [523.25, 659.25, 783.99, 1046.50]
            step = int(t / 0.12)
            freq = notes[min(step, len(notes) - 1)]
            env = math.exp(-(t % 0.12) * 8)
            return math.sin(2 * math.pi * freq * t) * env * 0.7

        # 8. Dice bounce / clack: hollow wooden knock
        def gen_clack(t, d):
            env = math.exp(-t * 90)
            return (math.sin(2 * math.pi * 380 * t) * 0.65 +
                    math.sin(2 * math.pi * 760 * t) * 0.35) * env * 0.75

        try:
            self.sounds['click'] = pygame.mixer.Sound(buffer=self._generate_pcm(gen_click, 0.03))
            self.sounds['dice'] = pygame.mixer.Sound(buffer=self._generate_pcm(gen_dice, 0.30))
            self.sounds['clack'] = pygame.mixer.Sound(buffer=self._generate_pcm(gen_clack, 0.05))
            self.sounds['move'] = pygame.mixer.Sound(buffer=self._generate_pcm(gen_move, 0.14))
            self.sounds['capture'] = pygame.mixer.Sound(buffer=self._generate_pcm(gen_capture, 0.32))
            self.sounds['extra_turn'] = pygame.mixer.Sound(buffer=self._generate_pcm(gen_extra_turn, 0.28))
            self.sounds['home'] = pygame.mixer.Sound(buffer=self._generate_pcm(gen_home, 0.45))
            self.sounds['victory'] = pygame.mixer.Sound(buffer=self._generate_pcm(gen_victory, 0.60))
        except Exception:
            pass


# Shared singleton instance
_GLOBAL_SOUND_MANAGER: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    global _GLOBAL_SOUND_MANAGER
    if _GLOBAL_SOUND_MANAGER is None:
        _GLOBAL_SOUND_MANAGER = SoundManager()
    return _GLOBAL_SOUND_MANAGER
