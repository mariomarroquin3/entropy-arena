import math
import os
import numpy as np
from ..base import EntropyMethod, EntropySample

_PI_BITS = 8_000_000
_cache = {}


def _bs(a, b):
    """Binary splitting de la serie de Chudnovsky."""
    if b - a == 1:
        if a == 0:
            Pab = Qab = 1
        else:
            Pab = (6 * a - 5) * (2 * a - 1) * (6 * a - 1)
            Qab = a * a * a * 10939058860032000
        Tab = Pab * (13591409 + 545140134 * a)
        return Pab, Qab, -Tab if a & 1 else Tab
    m = (a + b) // 2
    P1, Q1, T1 = _bs(a, m)
    P2, Q2, T2 = _bs(m, b)
    return P1 * P2, Q1 * Q2, Q2 * T1 + P1 * T2


def pi_fixed(nbits: int) -> int:
    """floor(pi * 2**nbits) (con bits de guarda)."""
    g = nbits + 64
    terms = g // 47 + 2
    _, Q, T = _bs(0, terms)
    sqrt_c = math.isqrt(10005 << (2 * g))
    pi = (Q * 426880 * sqrt_c) // T
    return pi >> 64


def _pi_bits() -> np.ndarray:
    if "bits" not in _cache:
        n = pi_fixed(_PI_BITS)
        raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
        _cache["bits"] = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))
    return _cache["bits"]


class PiBitsMethod(EntropyMethod):
    """Bits binarios de pi desde un offset aleatorio. Determinista y público:
    la única entropía es el offset (~log2(8e6) bits)."""
    name = "pi_binary_digits"
    category = "mathematical"
    is_deterministic = True
    theoretical_bits_per_unit = 0.0
    unit_description = "byte"

    def generate(self, nbytes: int) -> EntropySample:
        bits = _pi_bits()
        span = nbytes * 8
        offset = int.from_bytes(os.urandom(8), "big") % (bits.size - span)
        data = np.packbits(bits[offset:offset + span]).tobytes()
        return EntropySample(self.name, data, math.log2(bits.size - span),
                             {"offset": offset,
                              "note": "constante pública; entropía = elección del offset"})
