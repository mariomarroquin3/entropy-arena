"""Tests sensibles a estructura algebraica/espectral (NIST SP 800-22 §2.5, 2.6, 2.12
y complejidad lineal global). Aceptan bytes o un vector de bits."""
import math
import numpy as np
from scipy.stats import chi2

from .statistical_tests import _bits


def binary_matrix_rank(data, rows: int = 32, cols: int = 32) -> dict:
    """NIST §2.5: rangos de matrices 32x32 sobre GF(2)."""
    b = _bits(data)
    per = rows * cols
    n_mat = b.size // per
    if n_mat < 38:
        return {"name": "binary_matrix_rank", "p_value": 0.0, "pass": False, "reason": "muestra corta"}
    full = minus1 = 0
    for k in range(n_mat):
        blk = b[k * per:(k + 1) * per].reshape(rows, cols)
        r = [int("".join(map(str, row)), 2) for row in blk]
        rank = 0
        for bit in range(cols - 1, -1, -1):
            piv = next((i for i in range(rank, rows) if (r[i] >> bit) & 1), None)
            if piv is None:
                continue
            r[rank], r[piv] = r[piv], r[rank]
            for i in range(rows):
                if i != rank and (r[i] >> bit) & 1:
                    r[i] ^= r[rank]
            rank += 1
        full += rank == rows
        minus1 += rank == rows - 1
    rest = n_mat - full - minus1
    p_full, p_m1, p_rest = 0.2888, 0.5776, 0.1336
    stat = ((full - p_full * n_mat) ** 2 / (p_full * n_mat) + (minus1 - p_m1 * n_mat) ** 2 / (p_m1 * n_mat)
            + (rest - p_rest * n_mat) ** 2 / (p_rest * n_mat))
    p = math.exp(-stat / 2)
    return {"name": "binary_matrix_rank", "statistic": stat, "p_value": p, "pass": p >= 0.01}


def dft_spectral(data) -> dict:
    """NIST §2.6: picos del espectro por encima del 95% esperado."""
    b = _bits(data)
    n = b.size
    if n < 1000:
        return {"name": "dft_spectral", "p_value": 0.0, "pass": False, "reason": "muestra corta"}
    mag = np.abs(np.fft.fft(2.0 * b - 1.0))[: n // 2]
    thr = math.sqrt(math.log(1 / 0.05) * n)
    n0 = 0.95 * n / 2
    n1 = float(np.sum(mag < thr))
    d = (n1 - n0) / math.sqrt(n * 0.95 * 0.05 / 4)
    p = math.erfc(abs(d) / math.sqrt(2))
    return {"name": "dft_spectral", "statistic": d, "p_value": p, "pass": p >= 0.01}


def approximate_entropy(data, m: int = 2) -> dict:
    """NIST §2.12: frecuencia de patrones solapados de m y m+1 bits."""
    b = _bits(data)
    n = b.size

    def phi(mm):
        ext = np.concatenate([b, b[: mm - 1]]) if mm > 1 else b
        vals = np.zeros(n, dtype=np.int64)
        for k in range(mm):
            vals = (vals << 1) | ext[k:k + n]
        c = np.bincount(vals, minlength=2 ** mm) / n
        c = c[c > 0]
        return float(np.sum(c * np.log(c)))

    apen = phi(m) - phi(m + 1)
    stat = 2.0 * n * (math.log(2) - apen)
    p = float(chi2.sf(stat, 2 ** m))
    return {"name": "approx_entropy", "statistic": stat, "p_value": p, "pass": p >= 0.01}


def linear_complexity(data, n_bits: int = 65536) -> dict:
    """Complejidad lineal de la secuencia completa (Berlekamp-Massey sobre GF(2)).
    Una secuencia aleatoria de n bits tiene L ~ n/2; un LFSR/MT (estado de k bits)
    se detiene en L = k << n/2 en cuanto n > 2k. Contraste: p ~ 4^-(n/2 - L),
    aproximación de la distribución de la desviación (Rueppel)."""
    b = _bits(data)[:n_bits].tolist()
    n = len(b)
    if n < 1000:
        return {"name": "linear_complexity", "p_value": 0.0, "pass": False, "reason": "muestra corta"}
    c, bb, L, m, s = 1, 1, 0, -1, 0
    for i in range(n):
        s = (s << 1) | b[i]                    # bit 0 = s_i, bit k = s_{i-k}
        if (c & s).bit_count() & 1:
            t = c
            c ^= bb << (i - m)
            if 2 * L <= i:
                L, m, bb = i + 1 - L, i, t
    deficit = max(0.0, n / 2 - L)
    p = min(1.0, 4.0 ** (-deficit))
    return {"name": "linear_complexity", "statistic": L, "expected": n / 2,
            "p_value": p, "pass": p >= 0.01}


def strided_linear_complexity(data, stride: int = 32, n_bits: int = 45000, offset: int = 0) -> dict:
    """Complejidad lineal del flujo de UN bit de cada `stride` (p. ej. el mismo bit de
    palabras de 32 bits consecutivas). Expone generadores lineales sobre GF(2) con
    estado k bits (MT19937: k=19937) cuando n_bits > 2k, algo que la secuencia
    concatenada oculta porque su complejidad puede superar n/2."""
    b = _bits(data)
    if b.size < offset + stride * n_bits:
        return {"name": f"linear_complexity_s{stride}", "p_value": 0.0, "pass": False,
                "reason": "muestra corta"}
    res = linear_complexity(b[offset::stride][:n_bits], n_bits)
    res["name"] = f"linear_complexity_s{stride}"
    return res


def run_structure_tests(data, n_bits: int = 65536, strides=()) -> list:
    b = _bits(data)
    out = [binary_matrix_rank(b[:n_bits]), dft_spectral(b[:n_bits]), approximate_entropy(b[:n_bits]),
           linear_complexity(b[:n_bits], n_bits)]
    out += [strided_linear_complexity(b, st) for st in strides]
    return out
