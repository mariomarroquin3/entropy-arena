import math
import numpy as np
from .statistical_tests import monobit_test, runs_test, _bits


def frequency_within_block(data: bytes, block_size: int = 128) -> dict:
    bits = _bits(data)
    n = bits.size
    if n < block_size:
        return {"name": "block_frequency", "p_value": 0.0, "pass": False}
    m = n // block_size
    blocks = bits[:m * block_size].reshape(m, block_size)
    pi = blocks.mean(axis=1)
    chi = 4.0 * block_size * np.sum((pi - 0.5) ** 2)
    from scipy.stats import chi2
    p = float(chi2.sf(chi, m))
    return {"name": "block_frequency", "statistic": float(chi),
            "p_value": float(p), "pass": p >= 0.01}


def cumulative_sums(data: bytes, mode: int = 0) -> dict:
    bits = 2 * _bits(data).astype(int) - 1
    if bits.size == 0:
        return {"name": f"cumulative_sums_{'fwd' if mode == 0 else 'bwd'}", "p_value": 0.0, "pass": False}
    if mode == 1:
        bits = bits[::-1]
    S = np.cumsum(bits)
    z = int(np.max(np.abs(S)))
    n = bits.size
    if z == 0:
        return {"name": f"cumulative_sums_{'fwd' if mode == 0 else 'bwd'}", "p_value": 1.0, "pass": True}
    from scipy.stats import norm
    k1 = np.arange((-n // z + 1) // 4, (n // z - 1) // 4 + 1)
    k2 = np.arange((-n // z - 3) // 4, (n // z - 1) // 4 + 1)
    p1 = np.sum(norm.cdf((4 * k1 + 1) * z / math.sqrt(n)) -
                norm.cdf((4 * k1 - 1) * z / math.sqrt(n)))
    p2 = np.sum(norm.cdf((4 * k2 + 3) * z / math.sqrt(n)) -
                norm.cdf((4 * k2 + 1) * z / math.sqrt(n)))
    p = 1.0 - p1 + p2
    return {"name": f"cumulative_sums_{'fwd' if mode == 0 else 'bwd'}", "statistic": z,
            "p_value": float(p), "pass": p >= 0.01}


def longest_run_of_ones(data: bytes) -> dict:
    bits = _bits(data)
    n = bits.size
    if n < 128:
        return {"name": "longest_run_ones", "p_value": 0.0, "pass": False}
    M = 8
    N = n // M
    pi = np.array([0.2148, 0.3672, 0.2305, 0.1875])
    blocks = bits[:N * M].reshape(N, M)
    v = np.zeros(4, dtype=int)
    for block in blocks:
        max_run = cur = 0
        for b in block:
            cur = cur + 1 if b else 0
            max_run = max(max_run, cur)
        if max_run <= 1: v[0] += 1
        elif max_run == 2: v[1] += 1
        elif max_run == 3: v[2] += 1
        else: v[3] += 1
    chi = np.sum((v - N * pi) ** 2 / (N * pi))
    from scipy.stats import chi2
    p = float(chi2.sf(chi, 3))
    return {"name": "longest_run_ones", "statistic": float(chi),
            "p_value": float(p), "pass": p >= 0.01}


def run_all_nist_lite(data: bytes) -> list:
    return [
        monobit_test(data),
        runs_test(data),
        frequency_within_block(data),
        cumulative_sums(data, mode=0),
        cumulative_sums(data, mode=1),
        longest_run_of_ones(data),
    ]
