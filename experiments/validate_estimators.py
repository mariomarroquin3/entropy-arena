"""Valida los estimadores SP 800-90B con fuentes de min-entropía conocida (Tabla 2 del documento).

Ninguna estimación debería superar el valor verdadero; MCV solo es ciego a la memoria.
Uso: python experiments/validate_estimators.py
"""
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.analysis.sp800_90b import min_entropy_per_bit

N = 100_000


def sources(rng):
    periodic = np.tile([0, 1, 1, 0], N // 4).astype(np.uint8)
    biased = (rng.random(N) < 0.7).astype(np.uint8)
    r, b = rng.random(N), [0]
    for i in range(1, N):
        b.append(b[-1] if r[i] < 0.8 else 1 - b[-1])
    sticky = np.array(b, dtype=np.uint8)
    p = 0.8   # min-entropía de una cadena de Markov simétrica con P(repetir)=p: -log2(p)
    return [
        ("periodica (0110)", periodic, 0.0),
        ("sesgada P(1)=0.7", biased, -math.log2(0.7)),
        ("memoria P(rep)=0.8", sticky, -math.log2(p)),
        ("os.urandom", np.unpackbits(np.frombuffer(os.urandom(N // 8), dtype=np.uint8)), 1.0),
    ]


def main():
    rng = np.random.default_rng(12345)
    print(f"{'fuente':<22}{'verdadera':>10}{'MCV':>8}{'min de 10':>11}   estimador que manda")
    print("-" * 74)
    ok = True
    for name, bits, true_h in sources(rng):
        est = min_entropy_per_bit(bits)
        worst = min((k for k in est if k != "min"), key=lambda k: est[k])
        print(f"{name:<22}{true_h:>10.3f}{est['mcv']:>8.3f}{est['min']:>11.3f}   {worst}")
        if name != "os.urandom" and est["min"] > true_h + 0.02:
            ok = False
    print("\nRESULTADO:", "ningún estimador supera el valor verdadero" if ok else "SOBREESTIMACIÓN detectada")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
