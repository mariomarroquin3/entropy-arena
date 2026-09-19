"""Tests de estructura sobre fuentes seleccionadas: proporción de muestras que pasan."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entropy_arena.analysis.structure_tests import run_structure_tests
from entropy_arena.methods.computational.secrets_csprng import SecretsMethod
from entropy_arena.methods.computational.mersenne_twister import MersenneTwister
from entropy_arena.methods.computational.prng_family import RanduMethod, Pcg64Method
from entropy_arena.methods.mathematical.cellular_automata import Rule30Method
from entropy_arena.methods.mathematical.logistic_map import LogisticMapMethod
from entropy_arena.methods.mathematical.pi_digits import PiBitsMethod

N_SAMPLES = 10
NBYTES = 8192            # 65536 bits para rango, espectral, entropía aprox. y complejidad lineal
BIG = 45000 * 32 // 8    # 180 kB: 45000 bits de un mismo bit-de-palabra (> 2 x 19937)


def main():
    cheap = [SecretsMethod(), Pcg64Method(), MersenneTwister(seed=None), RanduMethod(), PiBitsMethod()]
    slow = [Rule30Method(), LogisticMapMethod()]   # generar 180 kB sería demasiado lento
    print()
    header = False
    for m in cheap + slow:
        strided = m in cheap
        passes = {}
        for _ in range(N_SAMPLES):
            data = m.generate(BIG if strided else NBYTES).data
            for r in run_structure_tests(data, strides=(32,) if strided else ()):
                passes.setdefault(r["name"], []).append(bool(r["pass"]))
        cols = ["binary_matrix_rank", "dft_spectral", "approx_entropy", "linear_complexity",
                "linear_complexity_s32"]
        if not header:
            print(f"{'Método':<38}" + "".join(f"{c[:20]:>21}" for c in cols))
            print("-" * (38 + 21 * len(cols)))
            header = True
        row = "".join(f"{sum(passes[c]) / len(passes[c]):>20.0%} " if c in passes else f"{'-':>21}"
                      for c in cols)
        print(f"{m.name[:37]:<38}" + row)
    print()
    print(f"(proporción de {N_SAMPLES} muestras que pasan; - = no evaluado por coste)")


if __name__ == "__main__":
    main()
