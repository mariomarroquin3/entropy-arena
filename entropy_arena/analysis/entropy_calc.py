import math
import zlib
import numpy as np
from scipy.stats import entropy as scipy_entropy


def shannon_entropy_per_byte(data: bytes) -> float:
    if not data:
        return 0.0
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    probs = counts / counts.sum()
    return float(scipy_entropy(probs, base=2))


def min_entropy_per_byte(data: bytes) -> float:
    if not data:
        return 0.0
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    pmax = counts.max() / counts.sum()
    if pmax <= 0:
        return 0.0
    return float(-math.log2(pmax))


def collision_entropy_per_byte(data: bytes) -> float:
    if not data:
        return 0.0
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256).astype(float)
    p = counts / counts.sum()
    pc = float(np.sum(p ** 2))
    if pc <= 0:
        return 0.0
    return float(-math.log2(pc))


def compression_ratio(data: bytes) -> float:
    if not data:
        return 1.0
    comp = zlib.compress(data, 9)
    return len(comp) / len(data)


def total_bits_claimed(sample) -> float:
    return sample.bits_claimed
