import os
import numpy as np
from ..base import EntropyMethod, EntropySample

SEED_BITS = 64.0  # techo real: semilla de os.urandom(8)


class BrownianMotionMethod(EntropyMethod):
    name = "brownian_motion"
    category = "mathematical"
    is_deterministic = True
    theoretical_bits_per_unit = 0.0
    unit_description = "byte"

    def __init__(self, dt: float = 1e-3):
        self.dt = dt

    def generate(self, nbytes: int) -> EntropySample:
        seed = int.from_bytes(os.urandom(8), "big")
        rng = np.random.default_rng(seed)
        n_steps = nbytes * 8
        increments = rng.normal(0.0, np.sqrt(self.dt), n_steps)
        bits = (increments > 0).astype(np.uint8)
        data = np.packbits(bits).tobytes()
        data = (data + b"\x00" * nbytes)[:nbytes]
        return EntropySample(
            self.name, data, SEED_BITS,
            {"dt": self.dt, "seed": seed,
             "note": "proceso estocástico determinista; entropía hereda del seed"}
        )
