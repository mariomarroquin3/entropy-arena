"""Diagnóstico de sesiones manuales (dados / monedas) y cota de entropía medida."""
import math
from collections import Counter
from scipy.stats import chisquare, norm

Z = 2.576


def mcv_bits_per_symbol(symbols: list, alphabet: int) -> float:
    """Min-entropy por símbolo con cota superior al 99% de la frecuencia máxima,
    acotada por el máximo teórico log2(alphabet)."""
    n = len(symbols)
    if n < 2:
        return 0.0
    p = max(Counter(symbols).values()) / n
    pu = min(1.0, p + Z * math.sqrt(p * (1 - p) / (n - 1)))
    return min(math.log2(alphabet), -math.log2(pu))


def _runs_p(bits: list) -> float:
    n = len(bits)
    pi = sum(bits) / n
    if n < 2 or pi in (0.0, 1.0):
        return 0.0
    v = 1 + sum(a != b for a, b in zip(bits, bits[1:]))
    z = abs(v - 2 * n * pi * (1 - pi)) / (2 * math.sqrt(2 * n) * pi * (1 - pi))
    return float(2 * norm.sf(z))


def dice_report(rolls: list) -> dict:
    n = len(rolls)
    counts = [rolls.count(f) for f in range(1, 7)]
    chi_p = float(chisquare(counts).pvalue) if n >= 30 else None  # esperado >= 5
    parity_p = _runs_p([r % 2 for r in rolls]) if n >= 2 else None
    repeats = sum(a == b for a, b in zip(rolls, rolls[1:]))
    return {
        "n": n, "counts": counts, "chi2_p": chi_p, "runs_parity_p": parity_p,
        "repeat_rate": repeats / max(1, n - 1), "expected_repeat_rate": 1 / 6,
        "bits_nominal": n * math.log2(6),
        "bits_measured": n * mcv_bits_per_symbol(rolls, 6),
        "min_rolls_for_128": math.ceil(128 / math.log2(6)),
    }


def coin_report(flips: list) -> dict:
    n = len(flips)
    bits = [1 if f == "H" else 0 for f in flips]
    pairs = list(zip(flips[0::2], flips[1::2]))
    kept = sum(a != b for a, b in pairs)
    return {
        "n": n, "heads": sum(bits), "runs_p": _runs_p(bits) if n >= 2 else None,
        "von_neumann_yield": kept / max(1, len(pairs)), "von_neumann_bits": kept,
        "bits_nominal": float(n),
        "bits_measured": n * mcv_bits_per_symbol(flips, 2),
        "min_flips_for_128": 128,
    }


def format_report(kind: str, r: dict) -> str:
    lines = [f"--- Diagnóstico {kind} (n={r['n']}) ---"]
    for k, v in r.items():
        if k == "n":
            continue
        lines.append(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    ok = r["bits_measured"] >= 128
    lines.append("  => " + ("suficiente (>=128 bits medidos)" if ok
                            else "INSUFICIENTE: registra más tiradas"))
    return "\n".join(lines)
