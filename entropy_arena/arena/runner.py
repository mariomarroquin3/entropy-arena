import os
import time
from pathlib import Path
from ..methods.base import EntropyMethod
from .scoring import (compute_metrics, aggregate_test, compute_quality,
                      mcv_min_entropy, verdict)

SCALAR_KEYS = ("shannon", "min_entropy", "collision", "compress", "autocorr")


class Arena:
    """nbytes=12500 (100 kbit) x n_samples=100: cumple m>=55 para el test de
    uniformidad de p-values y resolución razonable para NIST (§4.2)."""

    def __init__(self, nbytes: int = 12500, n_samples: int = 100,
                 results_dir: str = "data/results"):
        self.nbytes = nbytes
        self.n_samples = n_samples
        self.methods = []
        self.results = []
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._ref = None

    def register(self, method: EntropyMethod) -> "Arena":
        self.methods.append(method)
        return self

    def _min_ent_ref(self) -> float:
        """Min-entropy que alcanzaría una fuente ideal con este tamaño de muestra."""
        if self._ref is None:
            vals = [mcv_min_entropy(os.urandom(self.nbytes)) for _ in range(30)]
            self._ref = sum(vals) / len(vals)
        return self._ref

    def _run_one(self, method: EntropyMethod) -> dict:
        base = {"method": method.name, "category": method.category,
                "deterministic": method.is_deterministic}
        pvals, scal, seen = {}, {k: [] for k in SCALAR_KEYS}, set()
        bits, failed, errors, repeated = [], 0, [], 0
        t0 = time.perf_counter()

        for _ in range(self.n_samples):
            try:
                s = method.generate(self.nbytes)
            except Exception as e:
                failed += 1
                errors.append(str(e))
                continue
            if s.data in seen:  # entrada fija (CSV manual): muestras no independientes
                repeated += 1
                continue
            seen.add(s.data)
            m = compute_metrics(s.data)
            bits.append(min(s.bits_claimed, 8.0 * len(s.data)))
            for k in SCALAR_KEYS:
                scal[k].append(m[k])
            for k, p in m["p_values"].items():
                pvals.setdefault(k, []).append(p)

        elapsed = round(time.perf_counter() - t0, 3)
        n = len(bits)
        if n == 0:
            return {**base, "score": 0.0, "real_bits": 0.0, "verdict": "SIN MUESTRAS",
                    "metrics": {}, "tests": {}, "samples_ok": 0,
                    "samples_failed": failed,
                    "error": errors[0] if errors else "sin muestras",
                    "elapsed_s": elapsed}

        tests = {k: aggregate_test(v) for k, v in pvals.items()}
        metrics = {k: sum(v) / n for k, v in scal.items()}
        for k, v in pvals.items():
            metrics[f"{k}_p"] = sum(v) / n
        real_bits = sum(bits) / n
        score = compute_quality(tests, metrics["min_entropy"], self._min_ent_ref())
        note = None
        if n < 55:
            note = (f"solo {n} muestra(s) única(s): sin test de uniformidad, "
                    "proporciones poco fiables")
        return {**base, "score": score, "real_bits": round(real_bits, 1),
                "verdict": verdict(score, real_bits), "metrics": metrics,
                "tests": tests, "samples_ok": n, "samples_failed": failed,
                "samples_repeated": repeated, "note": note, "elapsed_s": elapsed}

    def run(self) -> list:
        self.results = []
        for m in self.methods:
            print(f"[arena] Ejecutando '{m.name}' ({m.category}) ...")
            self.results.append(self._run_one(m))
        self.results.sort(key=lambda r: r["score"], reverse=True)
        return self.results
