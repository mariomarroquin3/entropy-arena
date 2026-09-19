import os
import numpy as np
from ..base import EntropyMethod, EntropySample

SEED_BITS = 64.0  # techo real: semilla de os.urandom(8)


class Rule30Method(EntropyMethod):
    name = "rule30_cellular_automaton"
    category = "mathematical"
    is_deterministic = True
    theoretical_bits_per_unit = 0.0
    unit_description = "byte"

    def __init__(self, width: int = 256, warmup: int = 200):
        self.width = width
        self.warmup = warmup

    def generate(self, nbytes: int) -> EntropySample:
        seed = int.from_bytes(os.urandom(8), "big")
        rng = np.random.default_rng(seed)
        cells = rng.integers(0, 2, self.width).astype(np.uint8)
        centre = self.width // 2
        bits = np.empty(nbytes * 8, dtype=np.uint8)
        for step in range(self.warmup + bits.size):
            left = np.roll(cells, 1)
            right = np.roll(cells, -1)
            cells = (left ^ (cells | right)).astype(np.uint8)
            if step >= self.warmup:
                bits[step - self.warmup] = cells[centre]  # columna central (Wolfram)
        data = np.packbits(bits).tobytes()
        return EntropySample(self.name, data, SEED_BITS,
                             {"width": self.width, "seed": seed})
