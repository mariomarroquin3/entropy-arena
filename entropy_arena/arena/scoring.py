import math
import numpy as np
from scipy.stats import chi2

from ..analysis.entropy_calc import (
    shannon_entropy_per_byte, collision_entropy_per_byte, compression_ratio,
)
from ..analysis.statistical_tests import chi_squared_bytes, autocorrelation
from ..analysis.nist_lite import run_all_nist_lite

ALPHA = 0.01
MIN_SEED_BITS = 128.0  # umbral para considerar una seed criptográficamente útil


def mcv_min_entropy(data: bytes) -> float:
    """Min-entropy por byte, estimador MCV de NIST SP 800-90B (cota IC 99%)."""
    n = len(data)
    if n < 2:
        return 0.0
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    p = counts.max() / n
    pu = min(1.0, p + 2.576 * math.sqrt(p * (1 - p) / (n - 1)))
    return -math.log2(pu)


def compute_metrics(data: bytes) -> dict:
    """Métricas por muestra: p-values de cada test + descriptores."""
    if not data:
        return {}
    pvals = {t["name"]: t.get("p_value", 0.0) for t in run_all_nist_lite(data)}
    pvals["chi2_bytes"] = chi_squared_bytes(data).get("p_value", 0.0)
    return {
        "p_values": pvals,
        "shannon": shannon_entropy_per_byte(data),
        "min_entropy": mcv_min_entropy(data),
        "collision": collision_entropy_per_byte(data),
        "compress": compression_ratio(data),
        "autocorr": autocorrelation(data, lag=1),
    }


def aggregate_test(pvalues: list) -> dict:
    """Criterios NIST SP 800-22 §4.2: proporción de aprobados + uniformidad."""
    m = len(pvalues)
    pv = np.asarray(pvalues, dtype=float)
    rate = float((pv >= ALPHA).mean())
    p_hat = 1 - ALPHA
    low = p_hat - 3 * math.sqrt(p_hat * (1 - p_hat) / m)
    prop_ok = rate >= low
    if m >= 55:
        hist = np.histogram(pv, bins=10, range=(0, 1))[0]
        stat = float(np.sum((hist - m / 10) ** 2 / (m / 10)))
        unif_p = float(chi2.sf(stat, 9))
        unif_ok = unif_p >= 1e-4
    else:  # muestras insuficientes para el test de uniformidad
        unif_p, unif_ok = None, True
    return {"pass_rate": rate, "min_rate": low, "prop_ok": bool(prop_ok),
            "uniformity_p": unif_p, "uniformity_ok": bool(unif_ok),
            "ok": bool(prop_ok and unif_ok)}


def compute_quality(tests: dict, min_ent: float, min_ent_ref: float) -> float:
    """Calidad estadística 0-100: cuánto *parece* aleatorio. NO mide entropía real."""
    frac_ok = sum(t["ok"] for t in tests.values()) / max(1, len(tests))
    ent_ratio = min(1.0, min_ent / min_ent_ref) if min_ent_ref > 0 else 0.0
    return round(100.0 * (0.7 * frac_ok + 0.3 * ent_ratio), 2)


# Con 7 tests x 2 criterios, una fuente IDEAL falla algún criterio con probabilidad no
# despreciable (Q=90 = un test fallido). Se exige >= 2 tests fallidos (Q < 85) para rechazar.
LOOKS_RANDOM_Q = 85.0


def verdict(quality: float, real_bits: float) -> str:
    looks = quality >= LOOKS_RANDOM_Q
    strong = real_bits >= MIN_SEED_BITS
    if looks and strong:
        return "APTO"
    if looks:
        return "IMITA AZAR (entropía real insuficiente)"
    return "FALLA TESTS" + ("" if strong else " + poca entropía")
