import hashlib
import time
import numpy as np
from ...analysis.sp800_90b import min_entropy_per_bit
from ..base import EntropyMethod, EntropySample


class CpuJitterMethod(EntropyMethod):
    """LSB de deltas de perf_counter_ns alrededor de una carga fija.
    Fuente física (ruido de temporización) sin condicionar: sesgada/correlada."""
    name = "cpu_timing_jitter"
    _base_name = "cpu_timing_jitter"
    category = "physical"
    is_deterministic = False
    theoretical_bits_per_unit = None
    unit_description = "bit"

    def __init__(self, conditioned: bool = False):
        self.conditioned = conditioned
        self.name = self._base_name + ("_sha256" if conditioned else "_raw")

    def generate(self, nbytes: int) -> EntropySample:
        n = nbytes * 8
        deltas = np.empty(n, dtype=np.int64)
        clock = time.perf_counter_ns
        prev = clock()
        for i in range(n):
            x = 0
            for j in range(20):
                x += j * j
            now = clock()
            deltas[i] = now - prev
            prev = now
        # Windows resuelve a 100 ns: dividir por la granularidad para no tomar un LSB constante
        pos = deltas[deltas > 0]
        g = int(np.gcd.reduce(pos)) if pos.size else 1
        bits = ((deltas // max(g, 1)) & 1).astype(np.uint8)
        raw = np.packbits(bits).tobytes()
        est = min_entropy_per_bit(bits)  # SP 800-90B: mínimo de los estimadores
        h_raw = n * est["min"]
        if not self.conditioned:
            return EntropySample(self.name, raw, h_raw,
                                 {"estimators": est, "note": "bits crudos; entropía = min de estimadores 90B"})
        # condicionamiento: compresión con SHA-256 (32 B) por bloque de 8 B crudos
        # => solo válido si cada bloque aporta >= 256 bits; se acota por h_raw
        out = bytearray()
        block = max(1, nbytes // 64)
        for i in range(0, nbytes, block):
            out += hashlib.sha256(raw[i:i + block]).digest()
        data = bytes(out[:nbytes]) if len(out) >= nbytes else bytes(out)
        while len(data) < nbytes:
            data += hashlib.sha256(data).digest()
        return EntropySample(self.name, data[:nbytes], min(h_raw, 8.0 * nbytes),
                             {"note": "SHA-256 sobre bloques; bits reales acotados por h_raw"})
