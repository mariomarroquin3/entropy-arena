import os
import numpy as np
from ..base import EntropyMethod, EntropySample

SEED_BITS = 64.0  # techo real: semilla de os.urandom(8)


class LorenzAttractorMethod(EntropyMethod):
    name = "lorenz_attractor"
    category = "mathematical"
    is_deterministic = True
    theoretical_bits_per_unit = 0.0
    unit_description = "byte"

    def __init__(self, sigma=10.0, rho=28.0, beta=8.0 / 3.0,
                 dt=0.01, burn_in=5000):
        self.sigma = sigma
        self.rho = rho
        self.beta = beta
        self.dt = dt
        self.burn_in = burn_in

    def _step(self, s):
        x, y, z = s
        return (x + self.dt * self.sigma * (y - x),
                y + self.dt * (x * (self.rho - z) - y),
                z + self.dt * (x * y - self.beta * z))

    def generate(self, nbytes: int) -> EntropySample:
        seed = int.from_bytes(os.urandom(8), "big")
        rng = np.random.default_rng(seed)
        state = tuple(float(v) for v in 1.0 + rng.normal(0, 0.1, 3))
        for _ in range(self.burn_in):
            state = self._step(state)
        bits = []
        prev_x = state[0]
        while len(bits) < nbytes * 8:
            state = self._step(state)
            x = state[0]
            bits.append(1 if x > prev_x else 0)
            prev_x = x
        data = np.packbits(np.array(bits, dtype=np.uint8)).tobytes()[:nbytes]
        return EntropySample(self.name, data, SEED_BITS,
                             {"sigma": self.sigma, "rho": self.rho,
                              "beta": self.beta, "seed": seed})
