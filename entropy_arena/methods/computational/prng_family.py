import os
import numpy as np
from ..base import EntropyMethod, EntropySample


class RanduMethod(EntropyMethod):
    """RANDU (IBM, 1960s): LCG x' = 65539 x mod 2^31. Célebre por sus planos."""
    name = "randu_lcg"
    category = "computational"
    is_deterministic = True
    theoretical_bits_per_unit = 0.0
    unit_description = "byte"

    def generate(self, nbytes: int) -> EntropySample:
        x = (int.from_bytes(os.urandom(4), "big") & 0x7FFFFFFF) | 1
        out = bytearray()
        for _ in range(nbytes):
            x = (65539 * x) % 2 ** 31
            out.append(x >> 23)  # 8 bits más altos de los 31
        return EntropySample(self.name, bytes(out), 30.0,
                             {"note": "estado de 31 bits, seed impar => 30 bits reales"})


class Pcg64Method(EntropyMethod):
    """numpy default_rng(): PCG64 sembrado con SeedSequence (128 bits del SO)."""
    name = "numpy_pcg64"
    category = "computational"
    is_deterministic = True
    theoretical_bits_per_unit = 0.0
    unit_description = "byte"

    def generate(self, nbytes: int) -> EntropySample:
        ss = np.random.SeedSequence()
        rng = np.random.Generator(np.random.PCG64(ss))
        data = rng.integers(0, 256, nbytes, dtype=np.uint8).tobytes()
        return EntropySample(self.name, data, 128.0,
                             {"entropy": ss.entropy,
                              "note": "PRNG estadístico, no criptográfico; entropía = seed de 128 bits"})
