import math
import numpy as np
from scipy.stats import chisquare


def _bits(data) -> np.ndarray:
    if isinstance(data, np.ndarray):  # ya es un vector de bits (útil para tests NIST)
        return data.astype(np.uint8)
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def monobit_test(data: bytes) -> dict:
    bits = _bits(data)
    n = bits.size
    if n == 0:
        return {"name": "monobit", "p_value": 0.0, "pass": False}
    s = int(np.sum(2 * bits.astype(np.int64) - 1))
    s_obs = abs(s) / math.sqrt(n)
    p = math.erfc(s_obs / math.sqrt(2))
    return {"name": "monobit", "statistic": s_obs, "p_value": p, "pass": p >= 0.01}


def runs_test(data: bytes) -> dict:
    bits = _bits(data)
    n = bits.size
    if n == 0:
        return {"name": "runs", "p_value": 0.0, "pass": False}
    pi = bits.mean()
    if abs(pi - 0.5) >= 2.0 / math.sqrt(n):
        return {"name": "runs", "p_value": 0.0, "pass": False,
                "reason": "falla monobit preliminar"}
    v_obs = 1 + int(np.sum(bits[1:] != bits[:-1]))
    num = abs(v_obs - 2 * n * pi * (1 - pi))
    den = 2 * math.sqrt(2 * n) * pi * (1 - pi)
    p = math.erfc(num / den) if den > 0 else 0.0
    return {"name": "runs", "statistic": v_obs, "p_value": p, "pass": p >= 0.01}


def chi_squared_bytes(data: bytes) -> dict:
    if not data:
        return {"name": "chi2_bytes", "p_value": 0.0, "pass": False}
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    expected = len(data) / 256.0
    if expected <= 0:
        return {"name": "chi2_bytes", "p_value": 0.0, "pass": False}
    stat, p = chisquare(counts, f_exp=[expected] * 256)
    return {"name": "chi2_bytes", "statistic": float(stat),
            "p_value": float(p), "pass": p >= 0.01}


def autocorrelation(data: bytes, lag: int = 1) -> float:
    arr = np.frombuffer(data, dtype=np.uint8).astype(float)
    if arr.size <= lag:
        return 0.0
    a, b = arr[:-lag], arr[lag:]
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])
