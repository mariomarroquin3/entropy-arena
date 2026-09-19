import os
import numpy as np
from ..base import EntropyMethod, EntropySample

SEED_BITS = 64.0  # techo real: semilla de os.urandom(8)


class LogisticMapMethod(EntropyMethod):
    name = "logistic_map"
    category = "mathematical"
    is_deterministic = True
    theoretical_bits_per_unit = 0.0
    unit_description = "byte"

    def __init__(self, r: float = 3.99, x0: float = None, burn_in: int = 1000):
        self.r = r
        self.x0 = x0
        self.burn_in = burn_in

    def generate(self, nbytes: int) -> EntropySample:
        if self.x0 is not None:
            x = self.x0
            seed_used = None
        else:
            seed_used = int.from_bytes(os.urandom(8), "big")
            u = seed_used / 2 ** 64
            x = 0.5 + 0.4 * (u - 0.5)
        for _ in range(self.burn_in):
            x = self.r * x * (1.0 - x)
        bits = np.empty(nbytes * 8, dtype=np.uint8)
        for i in range(bits.size):
            x = self.r * x * (1.0 - x)
            bits[i] = int(x * 2 ** 30) & 1  # bit bajo: evita el sesgo del umbral 0.5
        data = np.packbits(bits).tobytes()[:nbytes]
        return EntropySample(self.name, data, SEED_BITS if seed_used is not None else 0.0,
                             {"r": self.r, "x0": self.x0, "seed": seed_used})
