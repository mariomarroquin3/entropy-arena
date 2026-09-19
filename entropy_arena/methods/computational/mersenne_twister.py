import random
from ..base import EntropyMethod, EntropySample


class MersenneTwister(EntropyMethod):
    name = "random.getrandbits (Mersenne Twister)"
    category = "computational"
    is_deterministic = True
    theoretical_bits_per_unit = 8.0
    unit_description = "byte"

    def __init__(self, seed: int = None):
        self.seed = seed
        self._rng = random.Random(seed)

    def generate(self, nbytes: int) -> EntropySample:
        bits = self._rng.getrandbits(nbytes * 8)
        data = bits.to_bytes(nbytes, "big")
        return EntropySample(
            self.name, data, 0.0,
            {"seed": self.seed,
             "warning": "PRNG NO criptográficamente seguro"}
        )
